import re

with open('src/MetaTrainingGameDashboardView.jsx', 'r') as f:
    content = f.read()

# Insert state and refs
hooks = """  const apiHost = typeof window !== 'undefined' ? (window.location.hostname || 'localhost') : 'localhost';
  const autoDebateTimerRef = useRef(null);

  // Auto-scroll logic
  const scrollRef = useRef(null);
  const [autoScroll, setAutoScroll] = useState(true);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    setAutoScroll(isAtBottom);
  };

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [debateRecord, isDebating, autoScroll]);
"""
content = content.replace("  const apiHost = typeof window !== 'undefined' ? (window.location.hostname || 'localhost') : 'localhost';\n  const autoDebateTimerRef = useRef(null);\n", hooks)

# Find the feed container and add scroll properties
target_container = """            {/* Turns Render Feed */}
            {debateRecord && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>"""

replacement_container = """            {/* Turns Render Feed */}
            {debateRecord && (
              <div 
                ref={scrollRef} 
                onScroll={handleScroll}
                style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem', overflowY: 'auto', maxHeight: '500px', paddingRight: '10px' }}
              >"""

content = content.replace(target_container, replacement_container)

with open('src/MetaTrainingGameDashboardView.jsx', 'w') as f:
    f.write(content)
print("Auto-scroll patched!")
