/**
 * Reference techniques — generated from the web repo's canonical
 * SECTIONS bundle (index.html line 1258), itself built from the
 * OPML pipeline. Keyed by position name (exactly as it appears
 * in the web data, e.g. 'Outside tie (You)' for Hand Fighting)
 * → perspective → heading → technique[].
 *
 * DO NOT EDIT BY HAND. Regenerate via
 * tools/regen-reference-techniques.py (extracts + flattens the
 * web SECTIONS). Content authority = Aaron via the OPML pipeline.
 */

export type ReferenceTechniqueMap = Record<
  string, // position name (web-data canonical, may include '(You)')
  Record<
    string, // perspective (Passer / Guard player / Attacker / etc)
    Record<
      string, // heading (Setups / Entries, Control, etc)
      string[] // technique names
    >
  >
>;

export const REFERENCE_TECHNIQUES: ReferenceTechniqueMap = {
  'Back Control': {
    'Attacker': {
      'Setups / Entries': ['Seat belt', 'Body triangle'],
      'Control': ['Chin strap', 'Chest to back pressure', 'Body triangle', 'Seat belt grip'],
      'Offence': ['Arm bar from back', 'Rear naked choke'],
      'Defence / Escapes': ['Defence'],
    },
    'Defender': {
      'Defence / Escapes': ['Defence'],
    },
  },
  'Berimbolo': {
    'Initiative': {
      'Control': ['Berimbolo', 'Knee wedge berimbolo', 'Rebolo off losing kick through', 'Double leg counter'],
      'Defence / Escapes': ['Back take', 'Back take'],
      'Offensive transitions': ['Back take → Back Control', 'Far arm underhook twister hook back take → Back Control', 'Far arm chair sit back take → Back Control', 'Kick through back take → Back Control'],
    },
  },
  'Butterfly ashi': {
    'Passer': {
      'Offence': ['Clear foot back step', 'Escape', 'Crab ride'],
      'Defence / Escapes': ['Defence'],
    },
    'Guard player': {
      'Offence': ['Clear foot back step', 'Escape', 'Crab ride'],
      'Defence / Escapes': ['Defence'],
    },
  },
  'Butterfly guard': {
    'Passer': {
      'Offence': ['Bodylock', 'High tripod', 'Early prevention', 'Shoulder crunch defence', 'Posture up pummel underhook', 'Posture up pummel underhook', 'Posture up pummel underhook', 'Wrestle ups', 'Subtopic'],
      'Defence / Escapes': ['Defence'],
    },
    'Guard player': {
      'Offence': ['Bodylock', 'High tripod', 'Early prevention', 'Shoulder crunch defence', 'Posture up pummel underhook', 'Posture up pummel underhook', 'Posture up pummel underhook', 'Wrestle ups', 'Subtopic'],
      'Defence / Escapes': ['Defence'],
    },
  },
  'Closed Guard': {
    'Passer': {
      'Offence': ['Knee through centre', 'knee too floor', 'smash pass', 'control leg step out', 'Crab ride shin block', 'Standing ankle grip push'],
      'Defence / Escapes': ['Defence'],
    },
    'Guard player': {
      'Offence': ['Knee through centre', 'knee too floor', 'smash pass', 'control leg step out', 'Crab ride shin block', 'Standing ankle grip push'],
      'Defence / Escapes': ['Defence'],
    },
  },
  'Collar tie (You)': {
    'You': {
      'Setups / Entries': ['Collar tie', 'Outside tie'],
      'Offence': ['Climb to back', 'Snatch single', 'ankle pick', 'front headlock', 'Framing on head', 'Underhook', 'Collar Tie and Inside Tie Snap Down', 'Overtie snap', 'Brush by snap', 'Head to head', 'Head to shoulder', 'Outside tie', 'Disengaging', 'Rear body lock', 'Snatch head inside single', 'Snatch head outside single'],
    },
    'Opponent': {
      'Setups / Entries': ['Collar tie', 'Outside tie'],
      'Offence': ['Climb to back', 'Snatch single', 'ankle pick', 'front headlock', 'Framing on head', 'Underhook', 'Collar Tie and Inside Tie Snap Down', 'Overtie snap', 'Brush by snap', 'Head to head', 'Head to shoulder', 'Outside tie', 'Disengaging', 'Rear body lock', 'Snatch head inside single', 'Snatch head outside single'],
    },
  },
  'Crab ride': {
    'Initiative': {
      'Setups / Entries': ['Inverted North south'],
      'Control': ['Knee staple', 'Leg drag', 'Hammer down', 'Back take', 'Leg drag', 'Knee staple', 'Back take', 'Side control', 'Back take', '`', 'Side control'],
      'Offensive transitions': ['Crab ride to back control → Back Control'],
    },
  },
  'De la riva': {
    'Passer': {
      'Offence': ['Headquarters', 'High tripod', 'Knee to flooor', 'Hammer down', 'Crab ride'],
      'Defence / Escapes': ['Defence'],
    },
    'Guard player': {
      'Offence': ['Headquarters', 'High tripod', 'Knee to flooor', 'Hammer down', 'Crab ride'],
      'Defence / Escapes': ['Defence'],
    },
  },
  'Front Headlock': {
    'Attacker': {
      'Setups / Entries': ['Snapdown from collar tie', 'Snapdown from underhook', 'Snapdown from outside tie', 'Snapdown from over tie'],
      'Control': ['Chin strap tricep front headlock', 'Hands locked front headlock', 'Hip position / sprawl', 'Angle off to dominant side'],
      'Offence': ['Go-behind to rear bodylock', 'Single leg rear bodylock (opponent circles away)', 'Whip by (opponent circles away fast)', 'Bolt cutter from chin strap → D\'Arce', 'Bolt cutter from chin strap → Japanese necktie', 'Bolt cutter from hands locked → D\'Arce', 'Hook leg', 'Head pinch from hands locked → Anaconda', 'Headspin from hands locked → Anaconda', 'Pinch front headlock to Anaconda', 'High elbow guillotine sit back', 'High elbow guillotine roll through (counter to roll defence)', 'Seatbelt roll-through'],
      'Defence': ['Opponent posts to stop go-behind', 'Opponent squares back up', 'Opponent drives into you', 'Opponent reaches for single', 'Opponent builds tripod posture', 'Pressure to break posture'],
      'Submissions': ['High elbow guillotine', 'High wrist guillotine', 'D\'Arce', 'Japanese necktie', 'Anaconda'],
      'Offensive transitions': ['Head in the hole go-behind → Wrestling rear bodylock', 'Head in the hole go-behind → Back Control', 'Single leg rear bodylock → Wrestling rear bodylock', 'Single leg rear bodylock → Back Control', 'Whip by → Wrestling rear bodylock', 'Whip by → Back Control', 'Pinch front headlock → Anaconda', 'Anaconda defence roll-through → Crucifix', 'Seatbelt roll-through → Seatbelt choking side up', 'Seatbelt roll-through → Seatbelt choking side down', 'Seatbelt roll-through → Seatbelt no hooks', 'D\'Arce defence lay to back → North South'],
    },
    'Defender': {
      'Setups / Entries': ['Opponent secures chin strap tricep front headlock', 'Opponent secures hands locked front headlock', 'Opponent catches front headlock after snapdown', 'Opponent catches front headlock during shot defence'],
      'Control': ['Post to stop the go-behind', 'Build base', 'Regain posture', 'Recover elbow position inside'],
      'Offence': ['Sucker drag', 'Peek-out', 'Sit-through', 'Re-attack on single'],
      'Defence': ['Push arm off (bolt cutter defence)', 'Lay to back and extend arm (D\'Arce defence)', 'Free leg (Japanese necktie defence)', 'Hide foot (Japanese necktie defence)', 'Arm and leg post (Anaconda defence)', 'Leg up (Head pinch defence)', 'Arm over high elbow (Guillotine defence)', 'Stripping leg (Guillotine defence)', 'Strip grip turn head (High wrist guillotine defence)'],
      'Offensive transitions': ['Peek-out → Back Control', 'Re-attack on single → Grounded head inside single leg'],
    },
  },
  'Grounded 50/50': {
    'Initiative': {
      'Setups / Entries': ['Example: Sweep single defence leading into Wrestling 50/50'],
      'Control': ['Control opponent\'s ankle OR tight waist on their far hip', 'Nearside arm controls far ankle OR tight waist toward their far hip', 'Mirrored turtle positions', 'Facing opposite directions', 'Similar control configuration'],
      'Offence': ['Example: Knock to side'],
      'Defence / Escapes': ['Example: Underhook their leg', 'Example: Go over-back with the other arm', 'Example: Drive them sideways', 'Side Control'],
      'Submissions': ['Example: Consolidate dominant position'],
      'Offensive transitions': ['Exit grounded 50/50 to side control → Side Control'],
    },
    'Defensive': {
      'Setups / Entries': ['Example: Opponent initiates Grounded 50/50 from Sweep single'],
      'Control': ['Example: Keep tight control of opponent\'s leg and build toward initiative'],
      'Defence / Escapes': ['Example: Transition to your own control (ankle grip OR hip/tight-waist grip)'],
    },
  },
  'Half Guard Passing': {
    'Passer': {
      'Control': ['Crossface', 'Double unders', 'Near side underhook', 'Head positioning', 'Mount', 'Knee cut'],
      'Defence / Escapes': ['Defence'],
      'Offensive transitions': ['Half guard passing to mount (knee slide) → Mount'],
    },
    'Guard player': {
      'Control': ['Crossface', 'Double unders', 'Near side underhook', 'Head positioning', 'Mount', 'Knee cut'],
      'Defence / Escapes': ['Defence'],
    },
  },
  'Half butterfly': {
    'Passer': {
      'Offence': ['High tripod', 'Bodylock'],
      'Defence / Escapes': ['Defence'],
    },
    'Guard player': {
      'Offence': ['High tripod', 'Bodylock'],
      'Defence / Escapes': ['Defence'],
    },
  },
  'Head inside single leg': {
    'Attacker': {
      'Control': ['Sweep single'],
      'Offence': ['Foot Lift Takedown', 'Limp Arm counter to Shin Whizzer', 'Running the Pipe counter to Shin Whizzer', 'Head Inside Double Leg counter to Shin Whizzer', 'Collar Tie Ankle Tap counter to Shin Whizzer', 'Rear Bodylock counter to Tripod Defence', 'Knock Over Rear Bodylock counter to Near Side Block Tripod', 'Iranian counter to Sprawl', 'Iranian to Rear Bodylock counter to Sprawl', 'Shelfing the Leg counter to Sprawl', 'Shelfing Leg through Grounded Shin Whizzer', 'Cut Back Single Leg counter to Sprawl'],
      'Defence / Escapes': ['Tripod Defence Near Side Block', 'Bail out', 'Shin Whizzer Front Headlock Counter', 'Grip Break Defence from Shin Whizzer', 'Inside Switch Tripod Defence', 'Bail out', 'Near Side Block counter to Iranian', 'Bail out', 'Grounded Shin Whizzer', 'How to Sprawl', 'Sprawl to Belly Whizzer'],
      'Offensive transitions': ['Foot lift finish → Side Control', 'Trip finish → Mount', 'Run the pipe → Back Control', 'Lift and return → Side Control'],
    },
    'Defender': {
      'Offence': ['Foot Lift Takedown', 'Limp Arm counter to Shin Whizzer', 'Running the Pipe counter to Shin Whizzer', 'Head Inside Double Leg Counter to Shin Whizzer', 'Collar Tie Ankle Tap Counter to Shin Whizzer', 'Rear Bodylock counter to Tripod Defence', 'Knock Over Rear Bodylock counter to Near Side Block Tripod', 'Iranian counter to Sprawl', 'Iranian to Rear Bodylock counter to Sprawl', 'Shelfing the Leg counter to Sprawl', 'Shelfing Leg through Grounded Shin Whizzer', 'Cut Back Single Leg counter to Sprawl'],
      'Defence / Escapes': ['Tripod Defence Near Side Block', 'Bail out', 'Shin Whizzer Front Headlock Counter', 'Grip Break Defence from Shin Whizzer', 'Inside Switch Tripod Defence', 'Bail out', 'Near Side Block counter to Iranian', 'Bail out', 'Grounded Shin Whizzer', 'How to Sprawl', 'Sprawl to Belly Whizzer'],
    },
  },
  'Head outside single leg': {
    'Attacker': {
      'Setups / Entries': ['Example: Outside tie'],
      'Control': ['Example: Good posture', 'Example: Hip extension', 'Example: Knee on the ground on the inside', 'Example: Other leg stepped up, ready to transition', 'Example: Four grips', 'Example: One hand reinforces the other', 'Example: Control extended below the knee'],
      'Offence': ['Running the Pipe', 'Hands locked', 'Complete double', 'Tripod breakdown', 'Crackdown'],
      'Defence / Escapes': ['Example: Crotch hold'],
      'Submissions': ['Example: Guillotine', 'Example: Kimura'],
    },
    'Defender': {
      'Offence': ['Running the Pipe', 'Hands locked', 'Complete double', 'Tripod breakdown', 'Crackdown'],
    },
  },
  'Headquarters': {
    'Passer': {
      'Offence': ['Side control', 'Head pressure into hip', 'Straight arms', 'Side control', 'J point', 'Mount', 'High tripod'],
      'Defence / Escapes': ['Defence'],
    },
    'Guard player': {
      'Offence': ['Side control', 'Head pressure into hip', 'Straight arms', 'Side control', 'J point', 'Mount', 'High tripod'],
      'Defence / Escapes': ['Defence'],
    },
  },
  'Inside tie (You)': {
    'You': {
      'Setups / Entries': ['Inside tie to sweep single'],
      'Offensive transitions': ['Inside tie to sweep single → Head inside single leg'],
    },
  },
  'J point': {
    'Passer': {
      'Setups / Entries': ['Hip post', 'Collar tie', 'Bullfighter'],
      'Control': ['J point control'],
      'Offence': ['Toreando', 'Leg drag', 'North South pass', 'Sprawl'],
      'Defence': ['Bicep curl', 'Bicep ride', 'C grip', 'Forearm pressure', 'Back swim', 'Stripping lasso', 'Deep Lasso', 'Reverse de la riva', 'K Guard', 'Clearing 2 frames on left shoulder', 'Clearing 2 frames on right shoulder', 'Clearing frames on each shoulder', 'Head frame', 'X guard', 'Good elbow positioning', 'Smash pass', 'Foot shoulder frame', 'Far shoulder clamp', 'Elevated hips'],
      'Offensive transitions': ['Toreando → Side Control', 'Leg drag → Side Control', 'North South pass → North South', 'Sprawl → Side Control', 'Back swim → North South', 'Stripping lasso → J point', 'Deep Lasso → North South', 'Reverse de la riva → J point', 'K Guard → Side Control'],
    },
  },
  'K guard': {
    'Passer': {
      'Offence': ['North south passing', 'Underhook mount', 'Crab ride'],
      'Defence / Escapes': ['Defence'],
    },
    'Guard player': {
      'Setups / Entries': ['Enter K Guard from De La Riva', 'Enter K Guard from Knee Shield Half Guard'],
      'Control': ['Hands controlling behind the opponent\'s knee', 'Foot tight to the opponent\'s hip', 'Pull the body underneath the opponent to increase connection', 'Transition to standard 50/50', 'Transition to saddle'],
      'Offence': ['North south passing', 'Underhook mount', 'Crab ride', 'Invert to Backside 50/50'],
      'Defence / Escapes': ['Defence'],
      'Submissions': ['Inside heel hook'],
    },
  },
  'Knee shield half guard': {
    'Passer': {
      'Offence': ['Sprawling split squat', 'Low head split squat'],
      'Defence / Escapes': ['Defence'],
    },
    'Guard player': {
      'Offence': ['Sprawling split squat', 'Low head split squat'],
      'Defence / Escapes': ['Defence'],
    },
  },
  'Low ankle': {
    'Attacker': {
      'Setups / Entries': ['From: Outside tie (You)', 'From: Inside tie (You)', 'From: Over/Under (You)'],
    },
    'Defender': {
      'Defence / Escapes': ['Sprawl', 'Whizzer', 'Crossface'],
    },
  },
  'Mount': {
    'Attacker': {
      'Setups / Entries': ['Nearside underhook side control to mount', 'Crossface side control to mount', 'Body lock pass to mount', 'Tripod pass to mount', 'Half guard to mount'],
      'Control': ['Vertical posture mount', 'Single arm chest wrap', 'S mount'],
      'Offence': ['Knee through to mounted triangle (opponent blocks arm walk-up)', 'S mount to arm bar (opponent defends triangle by raising arm)', 'Reverse D\'Arce'],
      'Defence': ['Kipping escape', 'Foot trap'],
      'Submissions': ['Head arm', 'Mounted triangle', 'Arm bar', 'Reverse D\'Arce'],
    },
  },
  'North South': {
    'Attacker': {
      'Control': ['Arms inside', 'Behind tricep grips', 'Collar tie', 'Overback', 'Reverse bodylock'],
      'Offence': ['North south choke', 'Kimura', 'Tarikoplata', 'Arm bar', 'Back take', 'D’arce'],
      'Defence / Escapes': ['Frames', 'Coil', 'Far shoulder foot hook', 'wrestle up', 'turtle'],
      'Offensive transitions': ['North south hip-switch recovery → Side Control', 'Gift wrap', 'Kimura', 'North south snap/front-headlock collect → Front Headlock', 'North south force turtle → Turtle'],
    },
    'Defender': {
      'Control': ['Arms inside', 'Behind tricep grips', 'Collar tie', 'Overback', 'Reverse bodylock'],
      'Offence': ['North south choke', 'Kimura', 'Tarikoplata', 'Arm bar', 'Back take', 'D’arce'],
      'Defence / Escapes': ['Frames', 'Coil', 'Far shoulder foot hook', 'wrestle up', 'turtle'],
      'Offensive transitions': ['Force turtle from north south → Turtle', 'North south to front headlock → Front Headlock', 'Gift wrap', 'Kimura', 'North south to side control → Side Control'],
    },
  },
  'Outside ashi': {
    'Passer': {
      'Control': ['Smash pass'],
      'Offence': ['Back take', 'Back take', 'Chair sit arm underhook'],
      'Defence / Escapes': ['Defence'],
    },
    'Guard player': {
      'Control': ['Smash pass'],
      'Offence': ['Back take', 'Back take', 'Chair sit arm underhook'],
      'Defence / Escapes': ['Defence'],
    },
  },
  'Outside tie (You)': {
    'You': {
      'Setups / Entries': ['knee pull sweep single', 'throw by', 'collar tie throw by', 'head inside single', 'double leg', 'brush by', 'Collar tie throw by to wrestling bodylock', '2 on 1'],
      'Offence': ['Brush by', 'Throw by'],
      'Offensive transitions': ['Outside tie to 2-on-1 → 2-on-1 (You)', 'Outside tie to double leg → Double leg', 'Outside tie to head inside single → Head inside single leg', 'Knee pull to sweep single → Head inside single leg'],
    },
  },
  'Over/Under (You)': {
    'You': {
      'Offence': ['Sweep single', 'Arm drag', 'Inside leg trip', 'Inside leg trip to scissor takedown', 'Knee tap'],
      'Offensive transitions': ['Snap down from over/under → Head inside single leg', 'Setups / Entries', 'Control', 'Offence', 'Defence', 'Offensive transitions'],
    },
  },
  'Quarter guard': {
    'Passer': {
      'Control': ['Side control'],
      'Offence': ['Rau drag', 'Shin pin', 'Mount', 'Shin pin', 'Back step J point', 'Hand positioning', 'Elbow blocking', 'Overback', 'Clampoing hip near side underhook', 'Z Guard', 'Arm and head position', 'Shoving leg down', 'Hip switch', 'Knee cut', 'Stepping over leg'],
      'Defence / Escapes': ['Knees facing same way', 'Early prevention', 'Clearing kimura', 'overhook back step', 'Early prevention hip clamp', 'Defence'],
    },
    'Guard player': {
      'Control': ['Side control'],
      'Offence': ['Rau drag', 'Shin pin', 'Mount', 'Shin pin', 'Back step J point', 'Hand positioning', 'Elbow blocking', 'Overback', 'Clampoing hip near side underhook', 'Z Guard', 'Arm and head position', 'Shoving leg down', 'Hip switch', 'Knee cut', 'Stepping over leg'],
      'Defence / Escapes': ['Knees facing same way', 'Early prevention', 'Clearing kimura', 'overhook back step', 'Early prevention hip clamp', 'Defence'],
    },
  },
  'Reverse de la riva': {
    'Passer': {
      'Control': ['Crab ride'],
      'Offence': ['I point'],
      'Defence / Escapes': ['Defence'],
    },
    'Guard player': {
      'Control': ['Crab ride'],
      'Offence': ['I point'],
      'Defence / Escapes': ['Defence'],
      'Offensive transitions': ['Reverse de la riva inversion to crab ride → Crab ride'],
    },
  },
  'Seated Guard': {
    'Passer': {
      'Offence': ['Overback', 'North south', 'Entries', 'Arm and head position', 'Shoving leg down', 'Hip switch', 'Knee cut', 'Stepping over leg', 'One arm deep one shallow', 'Tricep pressure', 'Head centered', 'Hips to ass', 'Pulling in', 'Flat back', 'Seated guard', 'mount', 'side control', 'Half butterfly', 'side control', 'side control', 'Head post windshield wiper', 'Half guard passing', 'Pinning feet', 'High knee', 'Bringing head to pummeling leg side', 'Stepping over opposite side', 'Using head to create room', 'Tight bodylock', 'Trap arm', 'Shoulder crunch defence'],
      'Defence / Escapes': ['Defence'],
    },
    'Guard player': {
      'Offence': ['Overback', 'North south', 'Entries', 'Arm and head position', 'Shoving leg down', 'Hip switch', 'Knee cut', 'Stepping over leg', 'One arm deep one shallow', 'Tricep pressure', 'Head centered', 'Hips to ass', 'Pulling in', 'Flat back', 'Seated guard', 'mount', 'side control', 'Half butterfly', 'side control', 'side control', 'Head post windshield wiper', 'Half guard passing', 'Pinning feet', 'High knee', 'Bringing head to pummeling leg side', 'Stepping over opposite side', 'Using head to create room', 'Tight bodylock', 'Trap arm', 'Shoulder crunch defence'],
      'Defence / Escapes': ['Defence'],
    },
  },
  'Shin pin': {
    'Passer': {
      'Offence': ['J point', 'Rau drag', 'North South', 'North south passing'],
      'Defence / Escapes': ['Defence'],
    },
    'Guard player': {
      'Offence': ['J point', 'Rau drag', 'North South', 'North south passing'],
      'Defence / Escapes': ['Defence'],
    },
  },
  'Side Control': {
    'Attacker': {
      'Control': ['Tight waist', 'Near side underhook', 'Crossface', 'Knee on belly'],
      'Offence': ['Far side underhook to Kimura', 'Far side underhook to Far side arm bar', 'Gift wrap to back take', 'Seatbelt to back', 'Knee on belly to mount'],
      'Submissions': ['North South Choke', 'D\'Arce', 'Far side arm bar', 'Von Flue', 'Kimura', 'Tarikoplata'],
      'Offensive transitions': ['Kimura back take → Back Control', 'Far side arm bar back take → Back Control', 'Gift wrap to back take → Back Control', 'Seatbelt to back → Back Control', 'Knee on belly to mount → Mount'],
    },
    'Defender': {
      'Defence': ['Wrestle up single leg', 'Wrestle up dog fight', 'Bring knee shield back in', 'Knee frame'],
    },
  },
  'Single leg X': {
    'Passer': {
      'Offence': ['Strip foot push knee through step leg passed to pass', 'Strip leg back step', 'Strip foot on hip hop over push pull out'],
      'Defence / Escapes': ['Defence'],
    },
    'Guard player': {
      'Offence': ['Strip foot push knee through step leg passed to pass', 'Strip leg back step', 'Strip foot on hip hop over push pull out'],
      'Defence / Escapes': ['Defence'],
    },
  },
  'Supine Guard': {
    'Passer': {
      'Control': ['Maintaining camping control points'],
      'Offence': ['J point', 'Bullfighter', 'Toreando', 'Head in pocket', 'Cross control', 'Scoop grip'],
      'Defence / Escapes': ['Defence', 'Duck under pass', 'Clearing early coils', 'Back step', 'Shimmying body', 'Cross control pass', 'Head in pocket pass', 'Single under pass', 'scoop grip', 'Cross control', 'Diving crab ride', 'Head in belly'],
      'Offensive transitions': ['Offensive transitions'],
    },
    'Guard player': {
      'Control': ['Maintaining camping control points'],
      'Offence': ['J point', 'Bullfighter', 'Toreando', 'Head in pocket', 'Cross control', 'Scoop grip'],
      'Defence / Escapes': ['Defence', 'Duck under pass', 'Clearing early coils', 'Back step', 'Shimmying body', 'Cross control pass', 'Head in pocket pass', 'Single under pass', 'scoop grip', 'Cross control', 'Diving crab ride', 'Head in belly'],
      'Offensive transitions': ['Offensive transitions'],
    },
  },
  'Turtle': {
    'Attacker': {
      'Control': ['Turtle bodylock'],
      'Offence': ['Back take', 'Back take', 'Single hook', 'Reverse d’arce', 'Back tale', 'Head an arn', 'Reverse d’arce', 'Near side tip over', 'Far side rolling backtake', 'Second hook', 'Far side crab smash', 'Lat hip grip', 'Near side tip over', 'Single hook'],
      'Defence / Escapes': ['Keep them outside of legs', 'Blocking space for hooks', 'Cartwheel', 'Inside switch', 'Fatman roll', 'Granby'],
      'Offensive transitions': ['Seat belt back take → Back Control', 'Spiral ride near side tip over → Side Control', 'Spiral ride far side tip over → Mount', 'Crab hook → Side Control', 'Single hook → Back Control'],
    },
    'Defender': {
      'Offence': ['Back take', 'Back take', 'Single hook', 'Reverse d’arce', 'Back tale', 'Head an arn', 'Reverse d’arce', 'Near side tip over', 'Far side rolling backtake', 'Second hook', 'Far side crab smash', 'Lat hip grip', 'Near side tip over', 'Single hook'],
      'Defence / Escapes': ['Keep them outside of legs', 'Blocking space for hooks', 'Cartwheel', 'Inside switch', 'Fatman roll', 'Granby'],
    },
  },
  'Underhook (You)': {
    'You': {
      'Setups / Entries': ['Head inside double', 'run the pipe', 'foot lift', 'Front side uchimata', 'Lift and dump', 'Mat return', 'Back take', 'Knee staple', 'Lift and dump', 'Snatch head inside Single', 'Knee tap', 'Front headlock', 'Snatch head outside sngle', 'head inside single', 'head outside single', 'Underhook throw by to wrestling bodylock', 'Over/Under'],
      'Offence': ['Knee tap'],
      'Offensive transitions': ['Underhook to head inside single → Head inside single leg', 'Underhook to front headlock → Front Headlock', 'Underhook to head outside single leg → Head outside single leg', 'Underhook to head outside single → Head outside single leg'],
    },
  },
  'Wrestling bodylock': {
    'Attacker': {
      'Setups / Entries': ['Underhook throw by to wrestling bodylock', 'Collar tie throw by to wrestling bodylock'],
      'Control': ['Setups / Entries', 'Control', 'Offence', 'Defence', 'Submissions', 'Offensive transitions', 'Setups / Entries', 'Control', 'Offence', 'Defence', 'Submissions', 'Offensive transitions', 'Setups / Entries', 'Control', 'Offence', 'Defence', 'Submissions', 'Offensive transitions', 'Setups / Entries', 'Control', 'Offence', 'Defence', 'Submissions', 'Offensive transitions', 'Tripod bodylock'],
      'Offence': ['Wrestling rear bodylock mat return', 'Wrestling rear bodylock lift and dump', 'Wrestling side bodylock front side uchimata', 'Wrestling side bodylock lift and dump'],
      'Offensive transitions': ['Wrestling rear bodylock to turtle → Turtle', 'Wrestling rear bodylock to crab ride → Crab ride'],
    },
  },
  'X guard': {
    'Passer': {
      'Control': ['Control foot clear other back step to pass'],
      'Offence': ['If wrestle up inside switch tripod'],
      'Defence / Escapes': ['Defence'],
    },
    'Guard player': {
      'Control': ['Control foot clear other back step to pass'],
      'Offence': ['If wrestle up inside switch tripod'],
      'Defence / Escapes': ['Defence'],
    },
  },
};

/** Total count of technique entries in the bundled reference. */
export const REFERENCE_TECHNIQUE_COUNT = 778;
