/**
 * Accessibility tree builder and DOM serializer with monotonic UID tagging.
 */

import { AXNode, ElementReference } from '../types.js';

export interface SnapshotResult {
  formattedTree: string;
  elements: ElementReference[];
  rootNode: AXNode;
}

export function getClientSnapshotScript(pageId: number, verbose: boolean = false): string {
  return `
    (function() {
      let uidCounter = 0;
      const elements = [];
      const pageId = ${pageId};

      function getAccessibleRole(el) {
        const explicitRole = el.getAttribute('role');
        if (explicitRole) return explicitRole;

        const tag = el.tagName.toLowerCase();
        switch (tag) {
          case 'a': return el.hasAttribute('href') ? 'link' : 'generic';
          case 'button': return 'button';
          case 'input': {
            const type = (el.getAttribute('type') || 'text').toLowerCase();
            if (['button', 'submit', 'reset'].includes(type)) return 'button';
            if (type === 'checkbox') return 'checkbox';
            if (type === 'radio') return 'radio';
            if (type === 'image') return 'button';
            return 'textbox';
          }
          case 'textarea': return 'textbox';
          case 'select': return 'combobox';
          case 'option': return 'option';
          case 'h1': case 'h2': case 'h3': case 'h4': case 'h5': case 'h6': return 'heading';
          case 'header': return 'banner';
          case 'nav': return 'navigation';
          case 'main': return 'main';
          case 'footer': return 'contentinfo';
          case 'aside': return 'complementary';
          case 'form': return 'form';
          case 'table': return 'table';
          case 'ul': case 'ol': return 'list';
          case 'li': return 'listitem';
          case 'img': return 'image';
          case 'p': return 'paragraph';
          case 'dialog': return 'dialog';
          default: return 'generic';
        }
      }

      function getAccessibleName(el) {
        if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
        if (el.getAttribute('aria-labelledby')) {
          const ref = document.getElementById(el.getAttribute('aria-labelledby'));
          if (ref) return ref.innerText.trim();
        }
        if (el.id) {
          const label = document.querySelector('label[for="' + el.id + '"]');
          if (label) return label.innerText.trim();
        }
        const parentLabel = el.closest('label');
        if (parentLabel) {
          return parentLabel.innerText.trim();
        }
        if (el.getAttribute('placeholder')) return el.getAttribute('placeholder');
        if (el.getAttribute('alt')) return el.getAttribute('alt');
        if (el.getAttribute('title')) return el.getAttribute('title');

        const tag = el.tagName.toLowerCase();
        if (['button', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'summary', 'option'].includes(tag)) {
          return el.innerText ? el.innerText.trim().slice(0, 100) : '';
        }
        return '';
      }

      function traverse(el, depth = 0) {
        if (!el || el.nodeType !== Node.ELEMENT_NODE) return null;

        const role = getAccessibleRole(el);
        const name = getAccessibleName(el);
        const tag = el.tagName.toLowerCase();
        const isInteractive = ['a', 'button', 'input', 'textarea', 'select', 'summary'].includes(tag) || el.hasAttribute('tabindex') || el.hasAttribute('role') || el.onclick != null;

        let uid = undefined;
        if (isInteractive || ['heading', 'link', 'textbox', 'button', 'checkbox', 'radio', 'combobox'].includes(role)) {
          uid = pageId + '_' + (uidCounter++);
          el.setAttribute('data-marionette-uid', uid);

          const rect = el.getBoundingClientRect();
          const attrs = {};
          for (let i = 0; i < el.attributes.length; i++) {
            attrs[el.attributes[i].name] = el.attributes[i].value;
          }

          elements.push({
            uid: uid,
            tagName: tag,
            selector: el.id ? '#' + el.id : (el.className ? tag + '.' + el.className.split(' ').filter(Boolean).join('.') : tag),
            text: name || el.value || '',
            attributes: attrs,
            boundingBox: {
              x: rect.x,
              y: rect.y,
              width: rect.width,
              height: rect.height
            }
          });
        }

        const node = {
          role: role,
          name: name || undefined,
          uid: uid,
          children: []
        };

        if (tag.startsWith('h') && tag.length === 2 && !isNaN(tag[1])) {
          node.level = parseInt(tag[1], 10);
        }

        if (tag === 'input' || tag === 'textarea') {
          node.value = el.value || '';
        }

        if (tag === 'input' && (el.type === 'checkbox' || el.type === 'radio')) {
          node.checked = el.checked;
        }

        if (el === document.activeElement && el !== document.body) {
          node.focused = true;
        }

        if (el.hasAttribute('disabled')) {
          node.disabled = true;
        }

        for (const child of el.children) {
          const childNode = traverse(child, depth + 1);
          if (childNode) {
            node.children.push(childNode);
          }
        }

        return node;
      }

      const root = traverse(document.body);
      const rootNode = {
        role: 'RootWebArea',
        name: document.title || 'Page',
        focused: document.activeElement === document.body,
        children: root ? [root] : []
      };

      return {
        rootNode: rootNode,
        elements: elements
      };
    })()
  `;
}

export function formatAxTree(node: AXNode, indent: number = 0, verbose: boolean = false): string {
  const spaces = '  '.repeat(indent);
  const parts: string[] = [spaces + node.role];

  if (node.name) {
    parts.push(`"${node.name}"`);
  }

  if (node.level !== undefined) {
    parts.push(`[level=${node.level}]`);
  }

  if (node.value !== undefined) {
    parts.push(`(value: "${node.value}")`);
  }

  if (node.url) {
    parts.push(`(url: ${node.url})`);
  }

  if (node.checked !== undefined) {
    parts.push(`[checked=${node.checked}]`);
  }

  if (node.disabled) {
    parts.push(`[disabled]`);
  }

  if (node.focused) {
    parts.push(`[focused]`);
  }

  if (node.uid) {
    parts.push(`[uid="${node.uid}"]`);
  }

  let line = parts.join(' ');
  const childLines: string[] = [];

  if (node.children && node.children.length > 0) {
    for (const child of node.children) {
      const childFormatted = formatAxTree(child, indent + 1, verbose);
      if (childFormatted.trim()) {
        childLines.push(childFormatted);
      }
    }
  }

  if (childLines.length > 0) {
    return [line, ...childLines].join('\n');
  }

  return line;
}

interface ParsedElement {
  tag: string;
  attrs: Record<string, string>;
  content: string;
  children: ParsedElement[];
}

function parseHtmlElements(html: string): ParsedElement[] {
  const results: ParsedElement[] = [];
  const tagRegex = /<([a-zA-Z0-9]+)([^>]*)(?:>(.*?)<\/\1>|\/>)/gis;
  let match;

  while ((match = tagRegex.exec(html)) !== null) {
    const tag = match[1].toLowerCase();
    const rawAttrs = match[2] || '';
    const innerHtml = match[3] || '';

    if (['script', 'style', 'head', 'meta', 'link'].includes(tag)) {
      continue;
    }

    const attrs: Record<string, string> = {};
    const attrRegex = /([a-zA-Z0-9_-]+)(?:=["']([^"']*)["'])?/g;
    let attrMatch;
    while ((attrMatch = attrRegex.exec(rawAttrs)) !== null) {
      attrs[attrMatch[1].toLowerCase()] = attrMatch[2] ?? '';
    }

    const children = innerHtml ? parseHtmlElements(innerHtml) : [];
    results.push({
      tag,
      attrs,
      content: innerHtml.replace(/<[^>]*>/g, '').trim(),
      children,
    });
  }

  return results;
}

export function parseHtmlToAxTree(html: string, pageId: number, title: string = 'Document'): SnapshotResult {
  let uidCounter = 0;
  const elements: ElementReference[] = [];

  const rootNode: AXNode = {
    role: 'RootWebArea',
    name: title,
    focused: true,
    children: [],
  };

  function processParsedElement(elem: ParsedElement): AXNode {
    const tag = elem.tag;
    const attrs = elem.attrs;
    let role = attrs['role'] || 'generic';
    let name = attrs['aria-label'] || attrs['placeholder'] || attrs['title'] || attrs['alt'] || elem.content.slice(0, 80);

    if (tag === 'button') role = 'button';
    else if (tag === 'a') role = 'link';
    else if (tag === 'input') {
      const type = attrs['type'] || 'text';
      if (['button', 'submit'].includes(type)) role = 'button';
      else if (type === 'checkbox') role = 'checkbox';
      else if (type === 'radio') role = 'radio';
      else role = 'textbox';
    } else if (tag === 'textarea') role = 'textbox';
    else if (tag === 'select') role = 'combobox';
    else if (tag.startsWith('h') && tag.length === 2) role = 'heading';
    else if (tag === 'header') role = 'banner';
    else if (tag === 'nav') role = 'navigation';
    else if (tag === 'main') role = 'main';
    else if (tag === 'footer') role = 'contentinfo';

    const isInteractive = ['a', 'button', 'input', 'textarea', 'select', 'summary'].includes(tag) || attrs['role'] !== undefined;

    let uid: string | undefined = undefined;
    if (isInteractive || ['heading', 'link', 'textbox', 'button', 'checkbox', 'radio', 'combobox'].includes(role)) {
      uid = `${pageId}_${uidCounter++}`;
      elements.push({
        uid,
        tagName: tag,
        selector: attrs['id'] ? `#${attrs['id']}` : (attrs['class'] ? `${tag}.${attrs['class'].split(' ').filter(Boolean).join('.')}` : tag),
        text: name || attrs['value'] || '',
        attributes: attrs,
        boundingBox: { x: 0, y: 0, width: 100, height: 30 },
      });
    }

    const node: AXNode = {
      role,
      name: name || undefined,
      uid,
      children: [],
    };

    if (tag.startsWith('h') && tag.length === 2 && !isNaN(parseInt(tag[1], 10))) {
      node.level = parseInt(tag[1], 10);
    }
    if (attrs['value']) {
      node.value = attrs['value'];
    }

    for (const child of elem.children) {
      const childNode = processParsedElement(child);
      node.children = node.children || [];
      node.children.push(childNode);
    }

    return node;
  }

  const parsedElements = parseHtmlElements(html);
  for (const elem of parsedElements) {
    const node = processParsedElement(elem);
    rootNode.children = rootNode.children || [];
    rootNode.children.push(node);
  }

  const formattedTree = formatAxTree(rootNode);

  return {
    formattedTree,
    elements,
    rootNode,
  };
}
