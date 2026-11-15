import pytest

from didyouship.bundles import MAX_BUNDLES, scan_bundles, script_urls

PAGE = "https://example.com/"

HTML = """
<script src="/assets/index-abc.js"></script>
<script type="module" src="https://cdn.example.com/chunk.js"></script>
<script src="https://www.googletagmanager.com/gtag/js?id=G-1"></script>
<script src="//unpkg.com/react@18.3.1/umd/react.production.min.js"></script>
<link rel="modulepreload" href="/assets/vendor-def.js">
<script src="/assets/index-abc.js#dup"></script>
<script src="data:text/javascript,alert(1)"></script>
<script>inline()</script>
"""


def test_script_urls_keeps_only_own_scripts_in_order():
    assert script_urls(HTML, PAGE, "example.com") == [
        "https://example.com/assets/index-abc.js",
        "https://cdn.example.com/chunk.js",
        "https://example.com/assets/vendor-def.js",
    ]


def test_script_urls_does_not_match_lookalike_domains():
    html = '<script src="https://notexample.com/a.js"></script><script src="https://example.com.evil.io/b.js"></script>'
    assert script_urls(html, PAGE, "example.com") == []


def test_script_urls_is_capped():
    html = "".join(f'<script src="/c{i}.js"></script>' for i in range(40))
    assert len(script_urls(html, PAGE, "example.com")) == MAX_BUNDLES


def fake_fetch(files: dict):
    calls = []

    def fetch(url, max_bytes):
        calls.append(url)
        if url in files:
            return 200, files[url]
        return 404, "Not found"
    fetch.calls = calls
    return fetch


def test_reports_secret_with_bundle_and_ignores_publishable_keys():
    files = {
        "https://example.com/assets/index-abc.js": 'const s="sk_live_' + "a" * 24 + '",p="pk_live_' + "b" * 24 + '";',
        "https://example.com/assets/vendor-def.js": "export default 1;",
        "https://cdn.example.com/chunk.js": "x=1",
    }
    report = scan_bundles(HTML, PAGE, "example.com", fake_fetch(files))
    assert report["secrets"] == {"Stripe secret key": ["https://example.com/assets/index-abc.js"]}
    assert report["source_maps"] == []
    assert len(report["bundles"]) == 3


def test_source_map_from_comment_and_from_dot_map_guess():
    files = {
        "https://example.com/assets/index-abc.js": "x=1\n//# sourceMappingURL=index-abc.js.map\n",
        "https://example.com/assets/index-abc.js.map": '{"version":3,"sources":["../src/App.tsx"],"mappings":"AAAA"}',
        "https://example.com/assets/vendor-def.js": "y=2",
        "https://example.com/assets/vendor-def.js.map": '{"version":3,"file":"v.js","sources":["src/main.ts"]}',
    }
    report = scan_bundles(HTML, PAGE, "example.com", fake_fetch(files))
    assert sorted(report["source_maps"]) == [
        "https://example.com/assets/index-abc.js.map",
        "https://example.com/assets/vendor-def.js.map",
    ]


@pytest.mark.parametrize("body,exposed", [
    ('{"version":3,"sources":[],"mappings":""}', False),                                   # empty map
    ('{"version":3,"sources":["turbopack:///node_modules/next/dist/polyfill.js"]}', False),  # framework only
    ('{"version":3,"sources":["webpack/bootstrap","webpack/runtime/x"]}', False),          # bundler runtime
    ('{"version":3,"sources":["../node_modules/react/index.js","../src/App.tsx"]}', True),
    ('{"version":3,"sources":["' + "src/a.ts\",\"" * 9000, True),                         # truncated, huge list
])
def test_source_map_must_reveal_own_code(body, exposed):
    files = {"https://example.com/a.js": "x", "https://example.com/a.js.map": body}
    report = scan_bundles('<script src="/a.js"></script>', PAGE, "example.com", fake_fetch(files))
    assert bool(report["source_maps"]) is exposed


def test_spa_html_fallback_for_map_is_not_a_source_map():
    files = {
        "https://example.com/assets/index-abc.js": "x=1",
        "https://example.com/assets/index-abc.js.map": "<!doctype html><html>app shell</html>",
    }
    html = '<script src="/assets/index-abc.js"></script>'
    report = scan_bundles(html, PAGE, "example.com", fake_fetch(files))
    assert report["source_maps"] == []


def test_inline_data_source_map_is_not_fetched():
    files = {"https://example.com/a.js": "x=1\n//# sourceMappingURL=data:application/json;base64,e30=\n"}
    fetch = fake_fetch(files)
    scan_bundles('<script src="/a.js"></script>', PAGE, "example.com", fetch)
    assert fetch.calls == ["https://example.com/a.js"]


def test_network_errors_are_swallowed():
    def boom(url, max_bytes):
        raise TimeoutError("slow")
    report = scan_bundles(HTML, PAGE, "example.com", boom)
    assert report["secrets"] == {} and report["source_maps"] == []


def test_no_scripts_means_no_fetches():
    fetch = fake_fetch({})
    assert scan_bundles("<html></html>", PAGE, "example.com", fetch)["bundles"] == []
    assert fetch.calls == []
