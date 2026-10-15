import sys
import re

file_path = "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/screen_life_companion.py"
with open(file_path, "r") as f:
    content = f.read()

# Replace extraction prompt logic to use config
old_prompt_call = """        target_url = self.router.get_preferred_route()
        prompt = self.optimizer.current_extraction_prompt.format(batch_text=batch_text)"""

new_prompt_call = """        target_url = self.router.get_preferred_route()
        from config_manager import load_config
        config = load_config()
        prof = config.get('user_profile', 'general')
        profile_instruction = f"The user profile is '{prof}'. Prioritize detecting repetitive tasks related to this profile."
        prompt = self.optimizer.current_extraction_prompt.format(batch_text=batch_text) + "\\n" + profile_instruction"""

if old_prompt_call in content:
    content = content.replace(old_prompt_call, new_prompt_call)

old_roi_check = """                                    roi_val = int(tm["content"].split("ROI:")[1].split("/")[0].strip())
                                    if roi_val >= 90:
                                        subprocess.Popen(["python3", HANDOFF_SCRIPT, "0", tm["content"]], start_new_session=True)"""

new_roi_check = """                                    roi_val = int(tm["content"].split("ROI:")[1].split("/")[0].strip())
                                    from config_manager import load_config
                                    thresh = load_config().get("automation_threshold_roi", 90)
                                    if roi_val >= thresh:
                                        subprocess.Popen(["python3", HANDOFF_SCRIPT, "0", tm["content"]], start_new_session=True)"""

if old_roi_check in content:
    content = content.replace(old_roi_check, new_roi_check)

with open(file_path, "w") as f:
    f.write(content)
