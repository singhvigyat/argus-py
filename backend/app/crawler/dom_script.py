"""Browser-side DOM extraction script executed via Playwright page.evaluate()."""

DOM_EXTRACTION_SCRIPT = """
() => {
  const validTags = new Set([
    'a', 'button', 'input', 'select', 'textarea', 'label',
    'h1', 'h2', 'h3', 'h4', 'p', 'li', 'img', 'nav', 'header', 'footer', 'form'
  ]);
  const results = [];
  let idCounter = 1;
  let sectionCounter = 1;
  const capturedNodes = new Set();

  for (const el of document.querySelectorAll('*')) {
    const tagInfo = el.tagName.toLowerCase();
    if (!validTags.has(tagInfo)) continue;

    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') continue;

    const rect = el.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) continue;
    if (rect.y < 0 || rect.y > window.innerHeight) continue;

    let ancestor = el.parentElement;
    let hasCapturedAncestor = false;
    while (ancestor) {
      if (capturedNodes.has(ancestor)) {
        hasCapturedAncestor = true;
        break;
      }
      ancestor = ancestor.parentElement;
    }
    if (hasCapturedAncestor) continue;

    const ariaLabel = el.getAttribute('aria-label') || '';
    const titleAttr = el.getAttribute('title') || '';
    const placeholder = el.placeholder || '';

    let rawText = el.innerText || el.value || el.alt || ariaLabel || titleAttr || placeholder || '';
    rawText = rawText.trim().substring(0, 80);

    const hasSvgChild = el.querySelector('svg') !== null;
    const hasImgChild = el.querySelector('img') !== null;
    const isImageOnly = rawText === '' && (tagInfo === 'img' || hasSvgChild || hasImgChild);
    const text = rawText !== '' ? rawText : (isImageOnly ? '[visual label — see screenshot]' : '');

    const fontSize = parseFloat(style.fontSize) || 0;

    let color = style.color || '';
    const treeWalker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null);
    let firstTextNode = treeWalker.nextNode();
    while (firstTextNode && firstTextNode.nodeValue && firstTextNode.nodeValue.trim() === '') {
      firstTextNode = treeWalker.nextNode();
    }
    if (firstTextNode && firstTextNode.parentElement) {
      color = window.getComputedStyle(firstTextNode.parentElement).color || color;
    }

    const backgroundColor = style.backgroundColor || '';
    const role = el.getAttribute('role') || '';
    const isClickable = tagInfo === 'a' || tagInfo === 'button' || style.cursor === 'pointer';

    let section = '';
    let curr = el;
    while (curr) {
      const curTag = curr.tagName.toLowerCase();
      if (curTag === 'header' || curTag === 'nav') { section = 'navigation'; break; }
      if (curTag === 'footer') { section = 'footer'; break; }
      if (curTag === 'form') { section = 'form'; break; }
      if (curTag === 'main') { section = 'main'; break; }
      if (curTag === 'section' || curTag === 'article') {
        section = curr.id || curr.getAttribute('aria-label') || `section_${sectionCounter++}`;
        break;
      }
      curr = curr.parentElement;
    }

    if (!section) {
      const percentage = rect.y / window.innerHeight;
      if (percentage <= 0.15) section = 'hero';
      else if (percentage <= 0.40) section = 'features';
      else if (percentage <= 0.65) section = 'content';
      else if (percentage <= 0.85) section = 'cta_or_pricing';
      else section = 'footer';
    }

    results.push({
      id: idCounter++,
      tag: tagInfo,
      text,
      x: Math.round(rect.x),
      y: Math.round(rect.y),
      width: Math.round(rect.width),
      height: Math.round(rect.height),
      fontSize: Math.round(fontSize),
      color,
      backgroundColor,
      role,
      ariaLabel,
      isClickable,
      section,
      imageOnly: isImageOnly,
    });
    capturedNodes.add(el);
  }

  return results;
}
"""
