/**
 * In-app 3D map tab — renders the live Lauburu Grappling Map
 * inside a WebView as a first-class app screen.
 *
 * Injects a small CSS block on load to hide website-only chrome
 * (header, auth buttons, feedback modal, loading skeleton) so
 * the user sees only the 3D graph canvas and position panels.
 * The selectors target stable element IDs from the hosted page.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Text, View } from '@/components/Themed';
import { useMapUiStore } from '../../src/store/map-ui-store';

const FULL_MAP_URL = 'https://www.lauburugrapplingmap.com/';
const MAP_FILTER_ACTIONS = [
  { label: 'All', action: 'all' },
  { label: 'My game', action: 'my_game' },
  { label: 'Learned', action: 'learned' },
  { label: 'Drilling', action: 'drilling' },
] as const;
const COLLAPSED_HANDLE_PEEK = 34;
const FILTER_PANEL_WIDTH = 128;

type MapNavState = { loading?: boolean; url?: string };
type MapProgressEvent = { nativeEvent: { progress: number } };
type MapErrorEvent = { nativeEvent: Record<string, unknown> & { statusCode?: number } };

let CachedWebViewComponent: any | null | undefined;

function getWebViewComponent(): any | null {
  if (CachedWebViewComponent !== undefined) return CachedWebViewComponent;
  try {
    const mod = require('react-native-webview');
    CachedWebViewComponent = mod?.WebView ?? mod?.default ?? null;
  } catch {
    CachedWebViewComponent = null;
  }
  return CachedWebViewComponent;
}

/**
 * Injected after page load to strip ALL website-level chrome so
 * the user sees only the 3D graph canvas and its native controls.
 *
 * The mobile app tab bar is the only navigation — website header,
 * view tabs, toolbars, floating buttons, onboarding, modals, and
 * account/feedback UI must all be hidden. We keep graph-specific
 * elements (#graph3dView, .node-popup, #g3dDetail) visible.
 *
 * Selectors target stable IDs and class names from the hosted
 * page. If the site adds new chrome, add the selector here.
 */
const INJECTED_CSS = `
  /* ── Site-level shell ────────────────────────────────────── */
  header,
  header[role="banner"]            { display: none !important; }
  .view-tabs                       { display: none !important; }
  .toolbar                         { display: none !important; }
  #refBottomBar                    { display: none !important; }
  #refFilterToggle                 { display: none !important; }
  .skip-link                       { display: none !important; }

  /* ── Account / auth / feedback chrome ────────────────────── */
  #authBtn                         { display: none !important; }
  #suggestBtn                      { display: none !important; }
  #suggestionModal                 { display: none !important; }
  #headerMenu                      { display: none !important; }

  /* ── Panels that duplicate app-owned surfaces ────────────── */
  #refHomePanel                    { display: none !important; }
  #referenceView                   { display: none !important; }
  #controlCentreView               { display: none !important; }
  #dailySuggestionCard             { display: none !important; }

  /* ── Onboarding / loading / diagnostics ──────────────────── */
  #refOnboarding                   { display: none !important; }
  .tutorial-overlay                { display: none !important; }
  #loadingSkeleton                 { display: none !important; }
  .skeleton-bar                    { display: none !important; }
  #refEmpty                        { display: none !important; }
  #kbdHelpPanel                    { display: none !important; }
  #diagPanel                       { display: none !important; }

  /* ── Floating buttons / AI panel ─────────────────────────── */
  #quickDrillFab                   { display: none !important; }
  #aiPanel                         { display: none !important; }

  /* ── Make the 3D graph fill the viewport ─────────────────── */
  #graph3dView {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    bottom: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    z-index: 1 !important;
  }

  #graph3dView,
  #graph3dView canvas {
    touch-action: manipulation !important;
    -webkit-user-select: none !important;
    user-select: none !important;
  }

  /* ── Keep graph-native detail visible above the full-bleed canvas */
  #g3dDetail,
  .note-panel,
  .node-popup {
    z-index: 10 !important;
  }

  /* ── Replace hosted control surfaces with app-owned mobile controls ─ */
  #g3dToolbar,
  #g3dOptions,
  #g3dLegend {
    display: none !important;
  }

  /* ── Hide hosted recenter / zoom / camera buttons ──────────── */
  [aria-label*="ecenter" i],
  [aria-label*="oom" i],
  [title*="ecenter" i],
  [title*="oom" i],
  .graph-control,
  .camera-control,
  .zoom-control,
  #recenterBtn,
  #zoomControls {
    display: none !important;
  }

  /* ── Suppress body scroll — graph handles its own interaction */
  body {
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
  }
`;

const STYLE_SENTINEL_ID = 'lauburu-app-chrome-hide';

/**
 * Runs BEFORE page content loads (document-start). This ensures the
 * diagnostic bridge and CSS injection happen even if the page never
 * finishes loading (which is the current blocker — onLoadEnd doesn't fire).
 */
const INJECTED_JS_BEFORE_CONTENT = `
  (function() {
    // Queue-based diagnostic bridge — available from document-start
    var _queue = [];
    function _diag(obj) {
      if (window.ReactNativeWebView && window.ReactNativeWebView.postMessage) {
        while (_queue.length) window.ReactNativeWebView.postMessage(JSON.stringify(_queue.shift()));
        window.ReactNativeWebView.postMessage(JSON.stringify(obj));
      } else {
        _queue.push(obj);
      }
    }
    // Make _diag globally available so the post-load script can use it too
    window.__mapDiag = _diag;
    _diag({ event: 'before_content_loaded', url: location.href });

    // Inject hide-chrome CSS as early as possible (prevents FOUC)
    var style = document.createElement('style');
    style.id = '${STYLE_SENTINEL_ID}';
    style.textContent = ${JSON.stringify(INJECTED_CSS)};
    (document.head || document.documentElement).appendChild(style);
    _diag({ event: 'css_injected_early' });

    // Flush retry for queued messages
    setTimeout(function() {
      if (window.ReactNativeWebView && _queue.length) {
        while (_queue.length) window.ReactNativeWebView.postMessage(JSON.stringify(_queue.shift()));
      }
      _diag({ event: 'flush_retry_200ms', bridge_available: !!window.ReactNativeWebView });
    }, 200);
  })();
  true;
`;

const INJECTED_JS = `
  (function() {
    // Reuse the diagnostic bridge set up by injectedJavaScriptBeforeContentLoaded.
    // If it didn't run (shouldn't happen), create a minimal fallback.
    var _diag = window.__mapDiag || function(obj) {
      if (window.ReactNativeWebView) window.ReactNativeWebView.postMessage(JSON.stringify(obj));
    };
    _diag({ event: 'post_load_js_running' });

    function snapVisibility(id) {
      var el = document.getElementById(id);
      if (!el) return 'missing';
      var s = window.getComputedStyle(el);
      if (s.display === 'none') return 'hidden';
      return el.offsetHeight > 0 ? 'visible' : 'zero-height';
    }

    function snapChrome() {
      // Check every selector we try to hide — report which ones
      // actually matched something in the live DOM.
      var selectors = [
        'header', '.view-tabs', '.toolbar', '#refBottomBar',
        '#refFilterToggle', '.skip-link', '#authBtn', '#suggestBtn',
        '#suggestionModal', '#headerMenu', '#refHomePanel',
        '#referenceView', '#controlCentreView', '#dailySuggestionCard',
        '#refOnboarding', '.tutorial-overlay', '#loadingSkeleton',
        '.skeleton-bar', '#refEmpty', '#kbdHelpPanel', '#diagPanel',
        '#quickDrillFab', '#aiPanel'
      ];
      var matched = [];
      var unmatched = [];
      selectors.forEach(function(sel) {
        var el = document.querySelector(sel);
        if (el) {
          var s = window.getComputedStyle(el);
          matched.push(sel + '(' + s.display + ')');
        } else {
          unmatched.push(sel);
        }
      });
      return { matched: matched, unmatched: unmatched };
    }

    function snapTabs() {
      var tabs = document.querySelectorAll('.view-tab');
      var info = [];
      tabs.forEach(function(tab) {
        info.push({
          text: (tab.textContent || '').trim(),
          active: tab.classList.contains('active'),
          dataView: tab.getAttribute('data-view'),
          dataTarget: tab.getAttribute('data-target'),
          href: tab.getAttribute('href'),
          id: tab.id || null,
          tag: tab.tagName
        });
      });
      return info;
    }

    // ── 1. Inject hide-chrome CSS ──────────────────────────────
    if (!document.getElementById('${STYLE_SENTINEL_ID}')) {
      var style = document.createElement('style');
      style.id = '${STYLE_SENTINEL_ID}';
      style.textContent = ${JSON.stringify(INJECTED_CSS)};
      document.head.appendChild(style);
    }
    _diag({ event: 'css_injected' });

    // ── 2. Activate the 3D graph view ──────────────────────────
    function isGraph3dVisible() {
      var g3d = document.getElementById('graph3dView');
      if (!g3d) return false;
      var s = window.getComputedStyle(g3d);
      return s.display !== 'none' && g3d.offsetHeight > 0;
    }

    function ensureChromeCss() {
      if (!document.getElementById('${STYLE_SENTINEL_ID}')) {
        var style = document.createElement('style');
        style.id = '${STYLE_SENTINEL_ID}';
        style.textContent = ${JSON.stringify(INJECTED_CSS)};
        document.head.appendChild(style);
        _diag({ event: 'css_injected' });
      }
    }

    function activate3DView(attempt) {
      if (isGraph3dVisible()) {
        _diag({ event: 'already_visible', attempt: attempt });
        return;
      }

      // Strategy A: structural data-attribute on .view-tab
      var tabs = document.querySelectorAll('.view-tab');
      var clicked = false;
      tabs.forEach(function(tab) {
        var target = tab.getAttribute('data-view')
          || tab.getAttribute('data-target')
          || tab.getAttribute('href')
          || '';
        if (target.indexOf('graph') !== -1 || target.indexOf('3d') !== -1 || target.indexOf('network') !== -1) {
          tab.click();
          clicked = true;
          _diag({ event: 'strategy_a', attempt: attempt, attr: target });
        }
      });
      if (clicked) return;

      // Strategy A2: loose text match on tab labels
      tabs.forEach(function(tab) {
        if (clicked) return;
        var text = (tab.textContent || '').trim().toLowerCase();
        if (text.indexOf('3d') !== -1 || text.indexOf('network') !== -1 || text.indexOf('graph') !== -1) {
          tab.click();
          clicked = true;
          _diag({ event: 'strategy_a2', attempt: attempt, text: text });
        }
      });
      if (clicked) return;

      // Strategy B: site keyboard shortcut 'G'
      _diag({ event: 'strategy_b', attempt: attempt });
      document.dispatchEvent(new KeyboardEvent('keydown', {
        key: 'g', code: 'KeyG', keyCode: 71, bubbles: true
      }));

      setTimeout(function() {
        if (isGraph3dVisible()) {
          _diag({ event: 'strategy_b_worked', attempt: attempt });
          return;
        }
        // Strategy C: brute-force display
        _diag({ event: 'strategy_c', attempt: attempt });
        var g3d = document.getElementById('graph3dView');
        if (g3d) g3d.style.display = 'block';
        var ref = document.getElementById('referenceView');
        if (ref) ref.style.display = 'none';
        var cc = document.getElementById('controlCentreView');
        if (cc) cc.style.display = 'none';
      }, 100);
    }

    function textFor(el) {
      return (
        el.getAttribute('aria-label') ||
        el.getAttribute('title') ||
        el.textContent ||
        ''
      ).trim().toLowerCase();
    }

    function clickFirstMatching(matchers) {
      var selectors = ['button', '[role="button"]', 'a', '[tabindex]'];
      for (var s = 0; s < selectors.length; s++) {
        var nodes = document.querySelectorAll(selectors[s]);
        for (var i = 0; i < nodes.length; i++) {
          var node = nodes[i];
          var text = textFor(node);
          for (var m = 0; m < matchers.length; m++) {
            if (text.indexOf(matchers[m]) !== -1) {
              node.click();
              return text;
            }
          }
        }
      }
      return null;
    }

    function focusSearch() {
      var input = document.querySelector('input[type="search"], input[placeholder*="Search" i], input[placeholder*="search" i]');
      if (input && input.focus) {
        input.focus();
        _diag({ event: 'search_focused', via: 'input' });
        return true;
      }
      var clicked = clickFirstMatching(['search']);
      _diag({ event: clicked ? 'search_opened' : 'search_missing', via: clicked || 'none' });
      return !!clicked;
    }

    function recenterGraph() {
      var clicked = clickFirstMatching(['recenter', 're-center', 'center', 'reset view', 'home']);
      _diag({ event: clicked ? 'recenter_clicked' : 'recenter_missing', via: clicked || 'none' });
      return !!clicked;
    }

    function suppressHostedMobileLeaks() {
      var selectors = ['button', '[role="button"]', 'a', '[tabindex]'];
      var hidden = [];
      for (var s = 0; s < selectors.length; s++) {
        var nodes = document.querySelectorAll(selectors[s]);
        for (var i = 0; i < nodes.length; i++) {
          var node = nodes[i];
          if (!(node instanceof HTMLElement)) continue;
          if (node.closest('#g3dDetail, .node-popup, .note-panel')) continue;
          var text = textFor(node);
          if (
            text.indexOf('recenter') !== -1 ||
            text.indexOf('re-center') !== -1 ||
            text === 'center' ||
            text.indexOf('reset view') !== -1
          ) {
            node.style.display = 'none';
            hidden.push(text || 'unnamed');
          }
        }
      }
      _diag({ event: 'hosted_mobile_leaks_suppressed', hidden: hidden.slice(0, 8), total: hidden.length });
    }

    function applyFilter(filterName) {
      var filters = {
        all: ['all'],
        my_game: ['my game'],
        learned: ['learned'],
        drilling: ['drilling']
      };
      var matchers = filters[filterName];
      if (!matchers) return false;
      var clicked = clickFirstMatching(matchers);
      if (clicked) {
        setTimeout(function() {
          lastDetailShownAt = Date.now();
          _diag({ event: 'selection_guard_armed', reason: 'filter_' + filterName });
        }, 250);
      }
      _diag({ event: clicked ? 'filter_applied' : 'filter_missing', filter: filterName, via: clicked || 'none' });
      return !!clicked;
    }

    function detailSurfaceVisible() {
      var selectors = ['#g3dDetail', '.node-popup', '.note-panel'];
      for (var i = 0; i < selectors.length; i++) {
        var el = document.querySelector(selectors[i]);
        if (!el) continue;
        var s = window.getComputedStyle(el);
        if (s.display !== 'none' && s.visibility !== 'hidden' && el.offsetHeight > 0) {
          return true;
        }
      }
      return false;
    }

    function isInsideDetail(target) {
      return target && target instanceof Element &&
        target.closest('#g3dDetail, .node-popup, .note-panel');
    }

    var lastDetailShownAt = 0;
    var SELECTION_PROTECT_MS = 1200;

    function markDetailVisible(reason) {
      lastDetailShownAt = Date.now();
      _diag({ event: 'selection_guard_armed', reason: reason });
    }

    // Track visibility transitions so React Native can hide its
    // global FABs while a node detail surface is on screen.
    var lastDetailVisibleEmitted = false;
    function emitDetailVisibility() {
      var nowVisible = detailSurfaceVisible();
      if (nowVisible !== lastDetailVisibleEmitted) {
        lastDetailVisibleEmitted = nowVisible;
        _diag({ event: nowVisible ? 'detail_open' : 'detail_close' });
      }
    }

    var detailObserver = new MutationObserver(function() {
      if (detailSurfaceVisible()) {
        markDetailVisible('detail_visible');
      }
      emitDetailVisibility();
    });
    detailObserver.observe(document.documentElement, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['class', 'style', 'hidden']
    });
    // Also poll at 400ms — guards against the panel being shown via
    // pure CSS class toggles that fire one observer event before we
    // attach.
    setInterval(emitDetailVisibility, 400);

    function guardDeselect(e) {
      if (isInsideDetail(e.target)) return;
      if (!detailSurfaceVisible()) return;
      var age = Date.now() - lastDetailShownAt;
      if (age > SELECTION_PROTECT_MS) return;
      e.stopPropagation();
      e.preventDefault();
      _diag({ event: 'selection_guard_blocked', type: e.type, age: age });
    }

    ['pointerup', 'mouseup', 'click', 'touchend'].forEach(function(evt) {
      document.addEventListener(evt, guardDeselect, true);
    });

    window.__lauburuEnsureMap3D = function(reason) {
      ensureChromeCss();
      activate3DView(reason || 'manual');
    };

    window.__lauburuMapUi = {
      focusSearch: focusSearch,
      recenter: recenterGraph,
      applyFilter: applyFilter
    };

    window.__lauburuEnsureMap3D('initial');
    suppressHostedMobileLeaks();
    setTimeout(function() { window.__lauburuEnsureMap3D('retry_400ms'); }, 400);
    setTimeout(function() { window.__lauburuEnsureMap3D('retry_1200ms'); suppressHostedMobileLeaks(); }, 1200);
    setTimeout(function() { window.__lauburuEnsureMap3D('retry_3000ms'); suppressHostedMobileLeaks(); }, 3000);

    // ── 3. Final diagnostic snapshot after all retries ──────────
    setTimeout(function() {
      _diag({
        event: 'final_snapshot',
        graph3dView: snapVisibility('graph3dView'),
        referenceView: snapVisibility('referenceView'),
        controlCentreView: snapVisibility('controlCentreView'),
        tabs: snapTabs(),
        chrome: snapChrome()
      });
    }, 4000);

    // ── 4. MutationObserver for CSS re-injection ───────────────
    var reinjections = 0;
    var observer = new MutationObserver(function() {
      if (!document.getElementById('${STYLE_SENTINEL_ID}')) {
        ensureChromeCss();
        reinjections++;
        _diag({ event: 'css_reinjected', count: reinjections });
      }
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
  })();
  true;
`;

export default function Map3DScreen() {
  const params = useLocalSearchParams<{ url?: string | string[] }>();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [loadError, setLoadError] = useState(false);
  const [controlsExpanded, setControlsExpanded] = useState(false);
  const webviewRef = useRef<any>(null);
  const manualInjectedRef = useRef(false);
  const WebViewComponent = getWebViewComponent();
  const setNodeDetailOpen = useMapUiStore((s) => s.setNodeDetailOpen);

  // ── RN-side lifecycle logging (appears even if WebView never loads) ──
  console.log('[MAP-DIAG] Map3DScreen mounted');

  // Reset the global node-detail flag whenever the Map screen unmounts
  // so the FABs reappear on every other tab.
  useEffect(() => {
    return () => setNodeDetailOpen(false);
  }, [setNodeDetailOpen]);

  const handleMessage = (event: { nativeEvent: { data: string } }) => {
    console.log('[MAP-DIAG] onMessage received');
    try {
      const msg = JSON.parse(event.nativeEvent.data);
      if (msg && typeof msg === 'object' && 'event' in msg) {
        if (msg.event === 'detail_open') setNodeDetailOpen(true);
        else if (msg.event === 'detail_close') setNodeDetailOpen(false);
      }
      console.log('[MAP-DIAG]', JSON.stringify(msg, null, 2));
    } catch {
      console.log('[MAP-DIAG] raw:', event.nativeEvent.data);
    }
  };

  const url = useMemo(() => {
    const raw = Array.isArray(params.url) ? params.url[0] : params.url;
    return raw && raw.length > 0 ? raw : FULL_MAP_URL;
  }, [params.url]);

  console.log('[MAP-DIAG] WebView url:', url);

  const runMapUiAction = (script: string) => {
    webviewRef.current?.injectJavaScript(`${script}; true;`);
  };

  const toggleControls = () => setControlsExpanded((value) => !value);

  const applyFilter = (action: (typeof MAP_FILTER_ACTIONS)[number]['action']) => {
    runMapUiAction(`window.__lauburuMapUi && window.__lauburuMapUi.applyFilter(${JSON.stringify(action)})`);
    setControlsExpanded(false);
  };

  if (!WebViewComponent) {
    return (
      <View style={[styles.container, styles.moduleFallback, { paddingTop: insets.top + 12 }]}>
        <Text style={styles.errorTitle}>3D map unavailable in this build</Text>
        <Text style={styles.errorBody}>
          This simulator runtime does not include the native WebView module.
        </Text>
        <Text style={styles.errorBody}>
          Rebuild or reinstall the dev client after adding `react-native-webview`, then reopen Map.
        </Text>
        <Pressable style={styles.fallbackButton} onPress={() => router.push('/reference')}>
          <Text style={styles.fallbackButtonText}>Open Reference instead</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <WebViewComponent
        ref={webviewRef}
        source={{ uri: url }}
        style={styles.webview}
        injectedJavaScriptBeforeContentLoaded={INJECTED_JS_BEFORE_CONTENT}
        injectedJavaScript={INJECTED_JS}
        originWhitelist={['https://*']}
        javaScriptEnabled
        domStorageEnabled
        allowsInlineMediaPlayback
        mediaPlaybackRequiresUserAction={false}
        setSupportMultipleWindows={false}
        cacheEnabled
        startInLoadingState
        onMessage={handleMessage}
        onNavigationStateChange={(navState: MapNavState) => {
          console.log('[MAP-DIAG] nav:', navState.loading ? 'loading' : 'done', navState.url?.slice(0, 80));
        }}
        onLoadProgress={({ nativeEvent }: MapProgressEvent) => {
          const pct = Math.round(nativeEvent.progress * 100);
          // Log progress at 25% intervals to avoid spam
          if (pct === 25 || pct === 50 || pct === 75 || pct === 100) {
            console.log('[MAP-DIAG] progress:', pct + '%');
          }
          // At 50%+ the DOM should exist — manually inject if onLoadEnd hasn't fired
          if (pct >= 50 && !manualInjectedRef.current) {
            manualInjectedRef.current = true;
            console.log('[MAP-DIAG] manual inject at', pct + '%');
            webviewRef.current?.injectJavaScript(INJECTED_JS);
          }
        }}
        onLoadStart={() => { console.log('[MAP-DIAG] WebView onLoadStart'); manualInjectedRef.current = false; setLoadError(false); }}
        onLoadEnd={() => {
          console.log('[MAP-DIAG] WebView onLoadEnd');
          webviewRef.current?.injectJavaScript(
            `window.__lauburuEnsureMap3D && window.__lauburuEnsureMap3D('react_native_onLoadEnd'); true;`,
          );
        }}
        onError={(e: MapErrorEvent) => { console.log('[MAP-DIAG] WebView onError', e.nativeEvent); setLoadError(true); }}
        onHttpError={(e: MapErrorEvent) => { console.log('[MAP-DIAG] WebView onHttpError', e.nativeEvent.statusCode); setLoadError(true); }}
        renderLoading={() => (
          <View style={styles.loading}>
            <ActivityIndicator size="large" color="#d4e157" />
            <Text style={styles.loadingText}>Loading 3D map…</Text>
          </View>
        )}
      />
      {!loadError ? (
        <>
          {/* Dismiss overlay — tapping the graph closes the filter panel */}
          {controlsExpanded ? (
            <Pressable
              style={StyleSheet.absoluteFill}
              onPress={() => setControlsExpanded(false)}
            />
          ) : null}
          <View
            pointerEvents="box-none"
            style={[
              styles.floatingControls,
              {
                bottom: Math.max(insets.bottom, 12) + 12,
                right: controlsExpanded ? 10 : -(FILTER_PANEL_WIDTH - COLLAPSED_HANDLE_PEEK),
              },
            ]}>
            {controlsExpanded ? (
              <View style={styles.filterMenu}>
                <Text style={styles.menuSectionLabel}>Explore</Text>
                {MAP_FILTER_ACTIONS.map((filter) => (
                  <Pressable
                    key={filter.action}
                    style={styles.filterChip}
                    onPress={() => applyFilter(filter.action)}>
                    <Text style={styles.filterChipText}>{filter.label}</Text>
                  </Pressable>
                ))}
                <View style={styles.filterDivider} />
                <Pressable
                  style={styles.filterChip}
                  onPress={() => {
                    runMapUiAction('window.__lauburuMapUi && window.__lauburuMapUi.focusSearch()');
                    setControlsExpanded(false);
                  }}>
                  <Text style={styles.filterChipText}>Search</Text>
                </Pressable>
                <View style={styles.filterDivider} />
                <Text style={styles.menuSectionLabel}>Learn</Text>
                <Pressable
                  style={styles.filterChip}
                  onPress={() => {
                    setControlsExpanded(false);
                    router.push('/syllabus');
                  }}>
                  <Text style={styles.filterChipText}>Belt syllabus</Text>
                </Pressable>
                <Pressable
                  style={styles.filterChip}
                  onPress={() => {
                    setControlsExpanded(false);
                    router.navigate('/reference');
                  }}>
                  <Text style={styles.filterChipText}>Reference</Text>
                </Pressable>
                <Pressable
                  style={[styles.filterChip, styles.filterChipPrimary]}
                  onPress={() => runMapUiAction('window.__lauburuMapUi && window.__lauburuMapUi.recenter()')}>
                  <Text style={styles.filterChipPrimaryText}>Center</Text>
                </Pressable>
                <Pressable
                  style={styles.filterChip}
                  onPress={() => setControlsExpanded(false)}>
                  <Text style={styles.filterChipText}>Done</Text>
                </Pressable>
              </View>
            ) : null}
            <Pressable
              style={[styles.railHandle, controlsExpanded && styles.railHandleActive]}
              onPress={toggleControls}>
              <Text style={styles.railHandleText}>{controlsExpanded ? 'Close' : 'Filters'}</Text>
            </Pressable>
          </View>
        </>
      ) : null}
      {loadError && (
        <View
          style={[
            styles.errorBanner,
            { bottom: Math.max(insets.bottom, 12) + 12 },
          ]}>
          <Text style={styles.errorTitle}>
            Couldn&apos;t load the 3D map
          </Text>
          <Text style={styles.errorBody}>
            Check network access, then switch tabs and come back to retry.
          </Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#050505',
  },
  moduleFallback: {
    justifyContent: 'center',
    paddingHorizontal: 18,
    gap: 10,
  },
  webview: {
    flex: 1,
    backgroundColor: '#050505',
  },
  floatingControls: {
    position: 'absolute',
    gap: 6,
    alignItems: 'flex-end',
  },
  filterMenu: {
    width: FILTER_PANEL_WIDTH,
    gap: 4,
    padding: 6,
    borderRadius: 14,
    backgroundColor: 'rgba(12,12,12,0.92)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  filterChip: {
    height: 32,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 8,
    paddingHorizontal: 10,
  },
  filterChipText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#f5f7f9',
  },
  filterChipPrimary: {
    backgroundColor: 'rgba(212,225,87,0.18)',
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.3)',
  },
  filterChipPrimaryText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#dce97b',
  },
  filterDivider: {
    height: 1,
    backgroundColor: 'rgba(255,255,255,0.08)',
    marginVertical: 2,
  },
  menuSectionLabel: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    opacity: 0.5,
    paddingHorizontal: 4,
    paddingTop: 2,
  },
  railHandle: {
    height: 34,
    width: FILTER_PANEL_WIDTH,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 17,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
    backgroundColor: 'rgba(12,12,12,0.88)',
    paddingHorizontal: 12,
  },
  railHandleActive: {
    backgroundColor: 'rgba(212,225,87,0.16)',
    borderColor: 'rgba(212,225,87,0.35)',
  },
  railHandleText: {
    color: '#f5f7f9',
    fontSize: 11,
    fontWeight: '700',
  },
  loading: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    paddingHorizontal: 24,
    backgroundColor: '#050505',
  },
  loadingText: {
    fontSize: 15,
    opacity: 0.8,
  },
  errorBanner: {
    position: 'absolute',
    left: 16,
    right: 16,
    bottom: 16,
    gap: 6,
    padding: 16,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(250,204,21,0.28)',
    backgroundColor: 'rgba(20,20,20,0.92)',
  },
  errorTitle: {
    fontSize: 16,
    fontWeight: '700',
  },
  errorBody: {
    fontSize: 13,
    lineHeight: 18,
    opacity: 0.78,
  },
  fallbackButton: {
    alignSelf: 'flex-start',
    marginTop: 6,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 12,
    backgroundColor: 'rgba(212,225,87,0.16)',
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.3)',
  },
  fallbackButtonText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#dce97b',
  },
});
