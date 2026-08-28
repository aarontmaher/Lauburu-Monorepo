/**
 * MCP Tool definitions for 29 tools matching chrome-devtools-mcp schema.
 */

import { Tool } from '@modelcontextprotocol/sdk/types.js';

export const TOOL_DEFINITIONS: Tool[] = [
  // 1. click
  {
    name: 'click',
    description: 'Clicks on the provided element',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        uid: { type: 'string', description: 'The uid of an element on the page from the page content snapshot' },
        dblClick: { type: 'boolean', description: 'Set to true for double clicks. Default is false.' },
        includeSnapshot: { type: 'boolean', description: 'Whether to include a snapshot in the response. Default is false.' },
      },
      required: ['pageId', 'uid'],
    },
  },
  // 2. close_page
  {
    name: 'close_page',
    description: 'Closes the page by its index. The last open page cannot be closed.',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'The ID of the page to close. Call list_pages to list pages.' },
      },
      required: ['pageId'],
    },
  },
  // 3. drag
  {
    name: 'drag',
    description: 'Drag an element onto another element',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        from_uid: { type: 'string', description: 'The uid of the element to drag' },
        to_uid: { type: 'string', description: 'The uid of the element to drop into' },
        includeSnapshot: { type: 'boolean', description: 'Whether to include a snapshot in the response. Default is false.' },
      },
      required: ['pageId', 'from_uid', 'to_uid'],
    },
  },
  // 4. emulate
  {
    name: 'emulate',
    description: 'Emulates various features on the target page.',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        viewport: { type: 'string', description: 'Emulate device viewports \'<width>x<height>x<devicePixelRatio>[,mobile][,touch][,landscape]\'.' },
        userAgent: { type: 'string', description: 'User agent to emulate. Set to empty string to clear the user agent override.' },
        colorScheme: { type: 'string', enum: ['dark', 'light', 'auto'], description: 'Emulate the dark or the light mode. Set to "auto" to reset to the default.' },
        geolocation: { type: 'string', description: 'Geolocation (`<latitude>,<longitude>`) to emulate.' },
        networkConditions: { type: 'string', enum: ['Offline', 'Slow 3G', 'Fast 3G', 'Slow 4G', 'Fast 4G'], description: 'Throttle network. Omit to disable throttling.' },
        cpuThrottlingRate: { type: 'number', minimum: 1, maximum: 20, description: 'Represents the CPU slowdown factor.' },
        extraHttpHeaders: { type: 'string', description: 'Extra HTTP headers as a JSON string object.' },
      },
      required: ['pageId'],
    },
  },
  // 5. evaluate_script
  {
    name: 'evaluate_script',
    description: 'Evaluate a JavaScript function inside the target page. Returns the response as JSON, so returned values have to be JSON-serializable.',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        function: { type: 'string', description: 'A JavaScript function declaration to be executed by the tool in the target page.' },
        args: { type: 'array', items: { type: 'string' }, description: 'An optional list of arguments to pass to the function.' },
        waitForStableDom: { type: 'boolean', description: 'Whether to wait for the DOM to settle. Defaults to true.' },
        dialogAction: { type: 'string', description: 'Handle dialogs while execution. "accept", "dismiss", or string for prompt.' },
        filePath: { type: 'string', description: 'The absolute or relative path to a file to save the script output to.' },
      },
      required: ['pageId', 'function'],
    },
  },
  // 6. fill
  {
    name: 'fill',
    description: 'Type text into an input, text area or select an option from a <select> element.',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        uid: { type: 'string', description: 'The uid of an element on the page from the page content snapshot' },
        value: { type: 'string', description: 'The value to fill in.' },
        includeSnapshot: { type: 'boolean', description: 'Whether to include a snapshot in the response. Default is false.' },
      },
      required: ['pageId', 'uid', 'value'],
    },
  },
  // 7. fill_form
  {
    name: 'fill_form',
    description: 'Fill out multiple form elements (inputs, selects, checkboxes, radios) at once.',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        elements: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              uid: { type: 'string', description: 'The uid of the element to fill out' },
              value: { type: 'string', description: 'Value for the element.' },
            },
            required: ['uid', 'value'],
          },
          description: 'Elements from snapshot to fill out.',
        },
        includeSnapshot: { type: 'boolean', description: 'Whether to include a snapshot in the response. Default is false.' },
      },
      required: ['pageId', 'elements'],
    },
  },
  // 8. get_console_message
  {
    name: 'get_console_message',
    description: 'Gets a console message by its ID. You can get all messages by calling list_console_messages.',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        msgid: { type: 'number', description: 'The msgid of a console message on the page from the listed console messages' },
      },
      required: ['pageId', 'msgid'],
    },
  },
  // 9. get_network_request
  {
    name: 'get_network_request',
    description: 'Gets a network request by an optional reqid, if omitted returns the currently selected request in the DevTools Network panel.',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        reqid: { type: 'number', description: 'The reqid of the network request.' },
        requestFilePath: { type: 'string', description: 'Path to save request body.' },
        responseFilePath: { type: 'string', description: 'Path to save response body.' },
      },
      required: ['pageId'],
    },
  },
  // 10. handle_dialog
  {
    name: 'handle_dialog',
    description: 'If a browser dialog was opened, use this command to handle it',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        action: { type: 'string', enum: ['accept', 'dismiss'], description: 'Whether to dismiss or accept the dialog' },
        promptText: { type: 'string', description: 'Optional prompt text to enter into the dialog.' },
      },
      required: ['pageId', 'action'],
    },
  },
  // 11. hover
  {
    name: 'hover',
    description: 'Hover over the provided element',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        uid: { type: 'string', description: 'The uid of an element on the page from the page content snapshot' },
        includeSnapshot: { type: 'boolean', description: 'Whether to include a snapshot in the response. Default is false.' },
      },
      required: ['pageId', 'uid'],
    },
  },
  // 12. lighthouse_audit
  {
    name: 'lighthouse_audit',
    description: 'Get Lighthouse score and reports for accessibility, SEO, best practices, and agentic browsing.',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        device: { type: 'string', enum: ['desktop', 'mobile'], default: 'desktop', description: 'Device to emulate.' },
        mode: { type: 'string', enum: ['navigation', 'snapshot'], default: 'navigation', description: 'Mode of audit.' },
        outputDirPath: { type: 'string', description: 'Directory for reports. If omitted, uses temporary files.' },
      },
      required: ['pageId'],
    },
  },
  // 13. list_console_messages
  {
    name: 'list_console_messages',
    description: 'List all console messages for the target page since the last navigation.',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        types: { type: 'array', items: { type: 'string' }, description: 'Filter messages by types.' },
        serviceWorkerId: { type: 'string', description: 'Filter messages by service worker.' },
        pageSize: { type: 'integer', exclusiveMinimum: 0, description: 'Maximum number of messages to return.' },
        pageIdx: { type: 'integer', minimum: 0, description: 'Page number to return (0-based).' },
        includePreservedMessages: { type: 'boolean', default: false, description: 'Return preserved messages.' },
        includeStackTraces: { type: 'boolean', default: false, description: 'Include stack trace.' },
      },
      required: ['pageId'],
    },
  },
  // 14. list_network_requests
  {
    name: 'list_network_requests',
    description: 'Lists the most recent requests for the target page since the last navigation.',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        resourceTypes: { type: 'array', items: { type: 'string' }, description: 'Filter requests by resource types.' },
        pageSize: { type: 'integer', exclusiveMinimum: 0, description: 'Maximum number of requests to return.' },
        pageIdx: { type: 'integer', minimum: 0, description: 'Page number to return (0-based).' },
        includePreservedRequests: { type: 'boolean', default: false, description: 'Return preserved requests.' },
      },
      required: ['pageId'],
    },
  },
  // 15. list_pages
  {
    name: 'list_pages',
    description: 'Get a list of pages open in the browser.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
  // 16. navigate_page
  {
    name: 'navigate_page',
    description: 'Go to a URL, or back, forward, or reload. Use project URL if not specified otherwise.',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        url: { type: 'string', description: 'Target URL (only type=url)' },
        type: { type: 'string', enum: ['url', 'back', 'forward', 'reload'], description: 'Navigate by URL, back, forward, or reload.' },
        timeout: { type: 'integer', description: 'Maximum wait time in milliseconds.' },
        initScript: { type: 'string', description: 'Script to execute before navigation.' },
        ignoreCache: { type: 'boolean', description: 'Ignore cache on reload.' },
        handleBeforeUnload: { type: 'string', enum: ['accept', 'dismiss'], description: 'Auto accept or dismiss beforeunload.' },
      },
      required: ['pageId'],
    },
  },
  // 17. new_page
  {
    name: 'new_page',
    description: 'Open a new tab and load a URL. Use project URL if not specified otherwise.',
    inputSchema: {
      type: 'object',
      properties: {
        url: { type: 'string', description: 'URL to load in a new page.' },
        background: { type: 'boolean', description: 'Whether to open in background.' },
        timeout: { type: 'integer', description: 'Maximum wait time in milliseconds.' },
        isolatedContext: { type: 'string', description: 'Isolated browser context name.' },
      },
      required: ['url'],
    },
  },
  // 18. performance_analyze_insight
  {
    name: 'performance_analyze_insight',
    description: 'Provides more detailed information on a specific Performance Insight of an insight set.',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        insightSetId: { type: 'string', description: 'The id for the specific insight set.' },
        insightName: { type: 'string', description: 'The name of the insight.' },
      },
      required: ['pageId', 'insightSetId', 'insightName'],
    },
  },
  // 19. performance_start_trace
  {
    name: 'performance_start_trace',
    description: 'Start a performance trace on the target webpage. Use to find frontend performance issues.',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        reload: { type: 'boolean', default: true, description: 'Automatically reload page after starting trace.' },
        autoStop: { type: 'boolean', default: true, description: 'Automatically stop trace.' },
        filePath: { type: 'string', description: 'File path to save raw trace data.' },
      },
      required: ['pageId'],
    },
  },
  // 20. performance_stop_trace
  {
    name: 'performance_stop_trace',
    description: 'Stop the active performance trace recording on the target webpage.',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        filePath: { type: 'string', description: 'File path to save raw trace data.' },
      },
      required: ['pageId'],
    },
  },
  // 21. press_key
  {
    name: 'press_key',
    description: 'Press a key or key combination. Use this when other input methods cannot be used.',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        key: { type: 'string', description: 'A key or combination (e.g., "Enter", "Control+A").' },
        includeSnapshot: { type: 'boolean', description: 'Whether to include a snapshot.' },
      },
      required: ['pageId', 'key'],
    },
  },
  // 22. resize_page
  {
    name: 'resize_page',
    description: 'Resizes the page\'s window so that the page has specified dimension',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        width: { type: 'number', description: 'Page width' },
        height: { type: 'number', description: 'Page height' },
      },
      required: ['pageId', 'width', 'height'],
    },
  },
  // 23. select_page
  {
    name: 'select_page',
    description: 'Select a page as a context for future tool calls.',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'The ID of the page to select.' },
        bringToFront: { type: 'boolean', description: 'Whether to bring page to front.' },
      },
      required: ['pageId'],
    },
  },
  // 24. take_heapsnapshot
  {
    name: 'take_heapsnapshot',
    description: 'Capture a heap snapshot of the target page.',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        filePath: { type: 'string', description: 'Path to save .heapsnapshot file.' },
      },
      required: ['pageId', 'filePath'],
    },
  },
  // 25. take_screenshot
  {
    name: 'take_screenshot',
    description: 'Take a screenshot of the page or element.',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        format: { type: 'string', enum: ['png', 'jpeg', 'webp'], default: 'png', description: 'Screenshot format.' },
        quality: { type: 'number', minimum: 0, maximum: 100, description: 'Compression quality.' },
        uid: { type: 'string', description: 'Element uid from snapshot.' },
        fullPage: { type: 'boolean', description: 'Take full page screenshot.' },
        filePath: { type: 'string', description: 'File path to save screenshot.' },
      },
      required: ['pageId'],
    },
  },
  // 26. take_snapshot
  {
    name: 'take_snapshot',
    description: 'Take a text snapshot of the target page based on the a11y tree. The snapshot lists page elements along with a unique identifier (uid).',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        verbose: { type: 'boolean', description: 'Whether to include all possible information available in full a11y tree.' },
        filePath: { type: 'string', description: 'File path to save snapshot.' },
      },
      required: ['pageId'],
    },
  },
  // 27. type_text
  {
    name: 'type_text',
    description: 'Type text using keyboard into a previously focused input',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        text: { type: 'string', description: 'The text to type' },
        submitKey: { type: 'string', description: 'Optional key to press after typing.' },
      },
      required: ['pageId', 'text'],
    },
  },
  // 28. upload_file
  {
    name: 'upload_file',
    description: 'Upload a file through a provided element.',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        uid: { type: 'string', description: 'Element uid from snapshot.' },
        filePaths: { type: 'array', items: { type: 'string' }, minItems: 1, description: 'One or more local file paths to upload.' },
        includeSnapshot: { type: 'boolean', description: 'Include snapshot in response.' },
      },
      required: ['pageId', 'uid', 'filePaths'],
    },
  },
  // 29. wait_for
  {
    name: 'wait_for',
    description: 'Wait for the specified text to appear on the selected page.',
    inputSchema: {
      type: 'object',
      properties: {
        pageId: { type: 'number', description: 'Targets a specific page by ID.' },
        text: { type: 'array', items: { type: 'string' }, minItems: 1, description: 'Non-empty list of texts to wait for.' },
        timeout: { type: 'integer', description: 'Maximum wait time in milliseconds.' },
      },
      required: ['pageId', 'text'],
    },
  },
];
