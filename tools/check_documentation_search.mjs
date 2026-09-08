/** Smoke-check built Sphinx search scripts without launching a browser.
 * Usage: node tools/check_documentation_search.mjs docs/_build/html
 */
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const root = path.resolve(process.argv[2] || 'docs/_build/html');
const read = name => fs.readFileSync(path.join(root, name), 'utf8');
const sidebar = read('reference/index.html').split('</nav>')[0];
assert.match(sidebar, /href="\.\.\/genindex.html">Full Function Index/);
assert.match(sidebar, /href="\.\.\/py-modindex.html">Python Module Index/);
for (const name of ['genindex.html', 'py-modindex.html']) assert.ok(fs.existsSync(path.join(root, name)));
const scripts = [...read('search.html').matchAll(/<script[^>]*src="([^"]+)"/g)].map(m => m[1].split('?')[0]);
assert.ok(scripts.indexOf('_static/documentation_options.js') < scripts.indexOf('_static/local-search.js'));
assert.ok(scripts.indexOf('_static/local-search.js') < scripts.indexOf('_static/searchtools.js'));
const reports = [];
for (const protocol of ['file:', 'http:', 'https:']) {
  let fetches = 0;
  const element = () => ({dataset: {}, classList: {add() {}}, appendChild(child) {return child;}});
  const context = vm.createContext({window: {location: {protocol}},
    document: {documentElement: {dataset: {content_root: './'}}, createElement: element, getElementById() {return null;}},
    _(text) {return text;}, _ready() {}, SPHINX_HIGHLIGHT_ENABLED: false,
    fetch() {fetches++; return Promise.resolve({text: () => ''});}, console});
  for (const name of ['_static/documentation_options.js', '_static/language_data.js', '_static/searchtools.js', 'searchindex.js'])
    vm.runInContext(read(name), context, {filename: name});
  // Before the fix Sphinx attempts a fetch even for a local file result.
  vm.runInContext('Search.output = document.createElement("ul"); _displayItem(["installation", "Installation", "", "", 1, "installation.rst", "text"], [], []);', context);
  assert.equal(fetches, 1);
  fetches = 0;
  vm.runInContext(read('_static/local-search.js'), context);
  vm.runInContext('_displayItem(["installation", "Installation", "", "", 1, "installation.rst", "text"], [], []);', context);
  assert.equal(fetches, protocol === 'file:' ? 0 : 1);
  const queries = {};
  for (const query of ['PSA', 'plan_metric_tasks', 'installation']) {
    const results = vm.runInContext(`Search._performSearch(...Search._parseQuery(${JSON.stringify(query)}))`, context);
    assert.ok(results.length > 0, query);
    for (const result of results) assert.ok(fs.existsSync(path.join(root, result[0] + '.html')), result[0]);
    queries[query] = results.length;
  }
  const absent = vm.runInContext('Search._performSearch(...Search._parseQuery("zznonexistentqueryzz"))', context);
  assert.equal(absent.length, 0);
  reports.push({protocol, summary_fetches: fetches, queries, empty_query_results: 0});
}
console.log(JSON.stringify({sidebar_links: 'passed', script_order: 'passed', search: reports,
  scope: 'Generated HTML and actual Sphinx JavaScript checks; not a live browser test.'}, null, 2));
