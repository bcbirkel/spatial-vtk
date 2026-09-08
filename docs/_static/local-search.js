// Browsers cannot fetch HTML snippets from file:// URLs. The search index
// itself loads as a script and still provides result titles and target links.
// Keep the normal Sphinx result summaries when documentation is served via HTTP.
if (window.location.protocol === "file:") {
  DOCUMENTATION_OPTIONS.SHOW_SEARCH_SUMMARY = false;
}
