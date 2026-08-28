import re

with open('src/ConsensusSpecialistSkillsDashboard.jsx', 'r') as f:
    content = f.read()

# Add a Revoke button next to active skills
revoke_target = """<span style={{ fontSize: '0.65rem', background: 'rgba(56,189,248,0.2)', color: '#38bdf8', padding: '2px 6px', borderRadius: '4px' }}>
                          Active
                        </span>"""

revoke_replacement = """<span style={{ fontSize: '0.65rem', background: 'rgba(56,189,248,0.2)', color: '#38bdf8', padding: '2px 6px', borderRadius: '4px' }}>
                          Active
                        </span>
                        <button style={{ marginLeft: '0.5rem', background: 'rgba(239, 68, 68, 0.2)', border: '1px solid #ef4444', color: '#fca5a5', padding: '2px 6px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.65rem' }} onClick={() => alert('Skill Revoked/Overriden!')}>
                          Revoke
                        </button>"""

content = content.replace(revoke_target, revoke_replacement)

with open('src/ConsensusSpecialistSkillsDashboard.jsx', 'w') as f:
    f.write(content)
print("ConsensusSpecialistSkillsDashboard patched!")
