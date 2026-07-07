# CSS Selectors Guide for Documentation Frameworks

Reference for identifying content areas, navigation, and noise elements in common documentation frameworks.

## Docusaurus (v2/v3)

```yaml
Content:
  main: "article.markdown, .theme-doc-markdown, [class*='docItemCol'] article"
  code_blocks: "pre code, .prism-code"

Navigation:
  sidebar: ".theme-doc-sidebar-container nav, .menu__list"
  sidebar_links: ".menu__link"
  breadcrumbs: ".breadcrumbs"

Remove:
  - ".theme-doc-footer, .pagination-nav"
  - ".theme-edit-this-page"
  - ".table-of-contents"
  - ".theme-doc-sidebar-container"
  - ".navbar"
  - "[class*='announcementBar']"
```

## GitBook

```yaml
Content:
  main: ".markdown-body, [data-testid='page.contentEditor'], .page-body"
  code_blocks: ".code-block pre, pre code"

Navigation:
  sidebar: "nav.sidebar, [data-testid='table-of-contents']"
  sidebar_links: "nav.sidebar a"

Remove:
  - ".page-footer"
  - "[data-testid='page.editButton']"
  - ".header-row"
  - "[class*='PageFeedback']"
```

## ReadTheDocs / Sphinx

```yaml
Content:
  main: ".document .body, .rst-content, [role='main']"
  code_blocks: ".highlight pre, .literal-block"

Navigation:
  sidebar: ".wy-nav-side nav, .sphinxsidebar"
  sidebar_links: ".wy-nav-side a, .sphinxsidebar a"

Remove:
  - ".rst-footer-buttons"
  - ".wy-breadcrumbs"
  - "[role='navigation']"
  - ".headerlink"
  - ".wy-nav-top"
```

## MkDocs (Material theme)

```yaml
Content:
  main: ".md-content article, .md-content__inner"
  code_blocks: ".highlight code, pre code"

Navigation:
  sidebar: ".md-sidebar--primary nav, .md-nav"
  sidebar_links: ".md-nav__link"

Remove:
  - ".md-footer"
  - ".md-header"
  - ".md-source"
  - "[data-md-component='outdated']"
  - ".md-content__button"
```

## Next.js Documentation Sites

```yaml
Content:
  main: "main article, main .content, #__next main, [class*='docs-content']"
  code_blocks: "pre code, [data-rehype-pretty-code-fragment] pre"

Navigation:
  sidebar: "nav[class*='sidebar'], aside nav"
  sidebar_links: "nav[class*='sidebar'] a"

Remove:
  - "footer"
  - "header, nav[class*='navbar']"
  - "[class*='feedback']"
  - "[class*='editOnGithub']"
  - "[class*='breadcrumb']"
```

## VuePress

```yaml
Content:
  main: ".theme-default-content, .content__default"
  code_blocks: "div[class*='language-'] pre code"

Navigation:
  sidebar: ".sidebar-links, .sidebar"
  sidebar_links: ".sidebar-link"

Remove:
  - ".page-edit"
  - ".page-nav"
  - ".header-anchor"
```

## Mintlify

```yaml
Content:
  main: "#content-area article, main article"
  code_blocks: "pre code, [class*='CodeGroup'] pre"

Navigation:
  sidebar: "nav[class*='sidebar']"
  sidebar_links: "nav[class*='sidebar'] a"

Remove:
  - "[class*='Feedback']"
  - "[class*='PageFooter']"
  - "header"
```

## Nextra

```yaml
Content:
  main: "main article, .nextra-content"
  code_blocks: "pre code"

Navigation:
  sidebar: "aside nav, .nextra-sidebar-container nav"
  sidebar_links: "aside nav a"

Remove:
  - "footer"
  - ".nextra-breadcrumb"
  - "nav[class*='navbar']"
  - "[class*='editLink']"
```

## Generic Fallbacks

When the framework is unknown, try these selectors in order:

```yaml
Content (try in order):
  1. "main article"
  2. "article"
  3. "[role='main']"
  4. "main"
  5. ".content, #content"
  6. ".post-content, .entry-content"
  7. ".markdown-body"
  8. "body"

Navigation (try in order):
  1. "nav[class*='sidebar']"
  2. "aside nav"
  3. ".sidebar nav"
  4. "#sidebar"

Always Remove:
  - "script, style, noscript"
  - "header, footer"
  - "nav[class*='navbar'], nav[class*='header']"
  - "[class*='cookie'], [class*='Cookie']"
  - "[class*='banner'], [class*='Banner']"
  - "[class*='popup'], [class*='modal']"
  - "[class*='ads'], [class*='advertisement']"
  - "[aria-hidden='true']"
  - "iframe"
```

## Detection Heuristics

How to identify which framework a site uses:

| Framework | Detection Signal |
|-----------|-----------------|
| Docusaurus | `<meta name="generator" content="Docusaurus">`, `__docusaurus` in HTML |
| GitBook | `gitbook` in meta/class names, `.gitbook-root` |
| ReadTheDocs | `readthedocs` in URL/meta, `.rst-content` |
| MkDocs | `mkdocs` in meta generator, `.md-content` |
| Next.js | `__next` div, `_next` in asset paths |
| VuePress | `vuepress` in meta, `.theme-default-content` |
| Mintlify | `mintlify` in meta/scripts |
| Nextra | `nextra` in class names or meta |
