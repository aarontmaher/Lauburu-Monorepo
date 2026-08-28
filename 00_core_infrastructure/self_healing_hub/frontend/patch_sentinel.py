import re

with open('src/LiveDeviceSentinelHUD.jsx', 'r') as f:
    content = f.read()

import_statement = "import React, { useState, useEffect } from 'react';\nimport { LineChart, Line, ResponsiveContainer } from 'recharts';"
content = content.replace("import React, { useState, useEffect } from 'react';", import_statement)

# Example sparkline data
spark_data = "const sparkData = [{v: 40}, {v: 45}, {v: 42}, {v: 50}, {v: 48}, {v: 55}, {v: 52}];"
content = content.replace("export default function LiveDeviceSentinelHUD() {", "export default function LiveDeviceSentinelHUD() {\n  " + spark_data)

sparkline_jsx = """<div style={{ height: '30px', width: '60px', marginTop: '4px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={sparkData}>
                  <Line type="monotone" dataKey="v" stroke="#38bdf8" strokeWidth={2} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>"""

content = content.replace("</div>\n      ))}", sparkline_jsx + "\n</div>\n      ))}")

with open('src/LiveDeviceSentinelHUD.jsx', 'w') as f:
    f.write(content)
print("Sentinel HUD patched!")
