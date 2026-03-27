"""Playwright browser tests — load the page in a real browser and catch JS errors."""

import threading
import time

import pytest
import uvicorn

from jam import db as _db_module


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    """Start the jam server on a random port with an isolated database."""
    db_path = tmp_path_factory.mktemp("browser") / "test.db"
    _db_module.init_db(db_path)

    # Patch the DB path at module level for the server process
    import jam.server as srv

    original_init = srv.init_db
    srv.init_db = lambda *a, **kw: None  # prevent re-init

    # Monkey-patch all db functions to use our test db
    db_funcs = [
        "db_create_application", "db_get_application", "db_list_applications",
        "db_update_application", "db_delete_application",
        "db_create_document", "db_get_document", "db_list_documents",
        "db_update_document", "db_delete_document",
        "db_create_version", "db_list_versions", "db_get_version",
    ]
    originals = {}
    for name in db_funcs:
        db_name = name.removeprefix("db_")
        original = getattr(_db_module, db_name)
        originals[name] = getattr(srv, name)
        setattr(srv, name, lambda *a, _fn=original, **kw: _fn(*a, db_path=db_path, **kw))

    # Also isolate settings functions so tests never touch the production DB
    for fn_name in ("get_all_settings", "set_setting", "set_settings_batch", "get_catalog"):
        original = getattr(_db_module, fn_name)
        originals[fn_name] = getattr(srv, fn_name)
        setattr(srv, fn_name, lambda *a, _fn=original, **kw: _fn(*a, db_path=db_path, **kw))

    config = uvicorn.Config(
        app=srv.app,
        host="127.0.0.1",
        port=0,  # random free port
        log_level="error",
    )
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server to be ready
    for _ in range(50):
        if server.started:
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("Server did not start in time")

    # Get the actual port
    sockets = server.servers[0].sockets
    port = sockets[0].getsockname()[1]

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=5)

    # Restore originals
    for name, orig in originals.items():
        setattr(srv, name, orig)
    srv.init_db = original_init


@pytest.fixture
def page(server):
    """Create a Playwright browser page with JS error collection."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        pg = context.new_page()

        js_errors = []
        pg.on("pageerror", lambda err: js_errors.append(str(err)))

        pg.js_errors = js_errors  # type: ignore[attr-defined]
        pg.base_url = server  # type: ignore[attr-defined]

        yield pg

        browser.close()


class TestBrowserPageLoad:
    """Tests that load the page in a real browser and verify no JS errors."""

    def test_no_js_errors_on_initial_load(self, page):
        """The main page must load without any JavaScript errors."""
        page.goto(f"{page.base_url}/api/v1/")
        page.wait_for_load_state("networkidle")

        assert page.js_errors == [], (
            f"JavaScript errors on page load:\n"
            + "\n".join(page.js_errors)
        )

    def test_page_title_renders(self, page):
        """The page title should be present in the DOM."""
        page.goto(f"{page.base_url}/api/v1/")
        page.wait_for_load_state("networkidle")

        heading = page.locator("h1").first
        assert heading.is_visible()
        assert "Job Application Manager" in heading.text_content()

    def test_no_js_errors_navigating_all_tabs(self, page):
        """Click every navigation tab and assert no JS errors are raised."""
        page.goto(f"{page.base_url}/api/v1/")
        page.wait_for_load_state("networkidle")

        # Collect all nav links/buttons that switch views
        nav_items = page.locator("nav a, nav button, .nav-link, .tab-btn, [data-tab]")
        count = nav_items.count()

        for i in range(count):
            item = nav_items.nth(i)
            if item.is_visible():
                item.click()
                # Give JS time to execute after tab switch
                page.wait_for_timeout(300)

        assert page.js_errors == [], (
            f"JavaScript errors while navigating tabs:\n"
            + "\n".join(page.js_errors)
        )

    def test_no_console_errors_on_load(self, page):
        """No console.error calls should happen during page load."""
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        page.goto(f"{page.base_url}/api/v1/")
        page.wait_for_load_state("networkidle")

        # Filter out expected/benign errors (e.g. failed fetches to kb that isn't running)
        unexpected = [
            e for e in console_errors
            if "favicon" not in e.lower()
        ]

        assert unexpected == [], (
            f"Console errors on page load:\n" + "\n".join(unexpected)
        )

    def test_no_js_errors_opening_modals(self, page):
        """Opening modals/dialogs should not trigger JS errors."""
        page.goto(f"{page.base_url}/api/v1/")
        page.wait_for_load_state("networkidle")

        # Try clicking any "add" or "new" buttons that might open modals
        triggers = page.locator("button:has-text('Add'), button:has-text('New'), button:has-text('Create'), [data-action='add']")
        count = triggers.count()

        for i in range(count):
            trigger = triggers.nth(i)
            if trigger.is_visible():
                trigger.click()
                page.wait_for_timeout(300)

        assert page.js_errors == [], (
            f"JavaScript errors when opening modals:\n"
            + "\n".join(page.js_errors)
        )


class TestTemplateSettings:
    """Tests that the Settings → Templates section shows the modern default templates."""

    def test_cv_template_shows_modern_default(self, page):
        """CV template textarea must contain the modern one-page default when nothing is stored."""
        page.goto(f"{page.base_url}/api/v1/")
        page.wait_for_load_state("networkidle")

        # Open settings
        page.click("#settings-btn")
        page.wait_for_timeout(300)

        # Navigate to the Templates sub-section
        page.click("button[data-section='templates']")
        page.wait_for_timeout(600)  # allow async fetch to complete

        cv_value = page.locator("#template-cv").input_value()
        assert "<<FULL-NAME: Jane Doe>>" in cv_value, (
            f"CV template textarea does not contain the modern default.\n"
            f"First 200 chars: {cv_value[:200]!r}"
        )
        assert "\\definecolor{accent}" in cv_value, (
            "CV template missing accent colour definition (not the modern template)"
        )

    def test_cover_letter_template_shows_simple_default(self, page):
        """Cover letter template textarea must contain the simple default when nothing is stored."""
        page.goto(f"{page.base_url}/api/v1/")
        page.wait_for_load_state("networkidle")

        page.click("#settings-btn")
        page.wait_for_timeout(300)

        page.click("button[data-section='templates']")
        page.wait_for_timeout(600)

        cl_value = page.locator("#template-cover-letter").input_value()
        assert "<<HIRING-MANAGER-NAME:" in cl_value, (
            f"Cover letter template does not contain the simple default.\n"
            f"First 200 chars: {cl_value[:200]!r}"
        )
        assert "<<OPENING-PARAGRAPH:" in cl_value, (
            "Cover letter template missing paragraph placeholders"
        )
