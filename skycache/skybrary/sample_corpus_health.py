"""Skybrary PD wave: health / emergency educational samples (v1.31).

Curated public-domain and traditional educational texts for clinic USB packs.
NOT medical advice, NOT diagnosis, NOT a substitute for trained care.
Not a complete archive. Not free commercial broadband.
"""

from __future__ import annotations

HEALTH_SAMPLES: list[dict] = [
    {
        "work_id": "skybrary-pd-handwash-historical-001",
        "title": {"en": "Hand hygiene principles (historical educational summary)"},
        "creators": ["Public-domain nursing and sanitation handbooks (curated)"],
        "subjects": ["health_edu", "safety", "medicine", "emergency"],
        "tier": 1,
        "priority_class": "health",
        "summary": {
            "en": "Historical hand-washing literacy for community health education - not clinical protocol."
        },
        "body": (
            "Hand Hygiene Principles (Historical Educational Summary)\n\n"
            "IMPORTANT: Educational literacy only. NOT medical advice. Follow current local health "
            "authority guidance for clinical practice.\n\n"
            "Semmelweis and later nursing literature stressed that clean hands reduce the spread of "
            "disease between patients and within households. Historical manuals taught:\n\n"
            "1. Wash hands before preparing food and after using the latrine.\n"
            "2. Wash hands before and after caring for a sick person when water and soap are available.\n"
            "3. Use clean water when possible; if water is scarce, prioritize handwashing for caregivers.\n"
            "4. Dry hands on a clean cloth when available.\n"
            "5. Teach children the same habits by example.\n\n"
            "Modern clinical settings use updated protocols, alcohol-based rubs when appropriate, "
            "and sterile technique taught by professionals. This summary is community literacy, "
            "not hospital procedure.\n\n"
            "[Curated from public-domain sanitation themes. Skybrary health pack. Not medical advice.]"
        ),
    },
    {
        "work_id": "skybrary-pd-water-sanitation-001",
        "title": {"en": "Safe water and latrine literacy (historical public-health summary)"},
        "creators": ["Public-domain sanitation education sources (curated)"],
        "subjects": ["health_edu", "safety", "water", "emergency"],
        "tier": 1,
        "priority_class": "health",
        "summary": {
            "en": "Village-scale water and sanitation literacy from historical public-health teaching - not engineering design."
        },
        "body": (
            "Safe Water and Latrine Literacy (Historical Public-Health Summary)\n\n"
            "IMPORTANT: Educational only. NOT engineering certification. NOT medical advice. "
            "Local authorities set standards for wells, tanks, and waste systems.\n\n"
            "Open educational public-health materials long emphasized:\n\n"
            "1. Keep drinking water sources separated from animal waste and latrines.\n"
            "2. Cover stored drinking water; use clean cups; avoid dipping dirty hands into jars.\n"
            "3. Boil water when boiling is feasible and fuel is available if contamination is suspected "
            "(historical advice; modern guidance may include other approved methods - follow local authority).\n"
            "4. Latrines should drain away from wells and streams when terrain allows.\n"
            "5. Wash hands after latrine use and before eating.\n"
            "6. Protect children from playing near open waste.\n\n"
            "Disaster settings increase contamination risk. Coordinate with trained WASH responders "
            "when present.\n\n"
            "[Curated educational summary. Skybrary emergency-health pack. Not medical advice.]"
        ),
    },
    {
        "work_id": "skybrary-pd-ors-literacy-001",
        "title": {"en": "Oral rehydration literacy (educational public-health overview)"},
        "creators": ["Open public-health education tradition (curated summary)"],
        "subjects": ["health_edu", "emergency", "medicine", "safety"],
        "tier": 1,
        "priority_class": "emergency",
        "summary": {
            "en": "Educational overview of why rehydration matters historically - not a recipe substitute for certified ORS programs."
        },
        "body": (
            "Oral Rehydration Literacy (Educational Overview)\n\n"
            "IMPORTANT: This is educational background only. It is NOT a clinical protocol, "
            "NOT a home-made medicine recipe, and NOT a substitute for WHO/UNICEF or national "
            "ORS programs. Severe diarrhea and dehydration are medical emergencies - seek trained care.\n\n"
            "Historical and modern public-health teaching emphasizes that dehydration from diarrhea "
            "can kill quickly, especially young children. Community literacy goals often include:\n\n"
            "1. Recognizing danger signs: very little urine, extreme thirst, lethargy, sunken eyes, "
            "inability to drink - seek skilled care urgently.\n"
            "2. Continuing to offer fluids as advised by local health workers during mild illness when "
            "safe fluids are available.\n"
            "3. Using only approved oral rehydration salts when provided by health programs; do not invent "
            "unmeasured salt-sugar mixes without trained instruction.\n"
            "4. Hand hygiene and safe water reduce diarrhea risk (see related Skybrary sanitation notes).\n"
            "5. Exclusive breastfeeding guidance for infants belongs to trained maternal-child health programs.\n\n"
            "Operators packaging open ORS training materials must confirm license and keep national "
            "protocol sheets current.\n\n"
            "[Educational literacy only. Skybrary emergency-health pack. Not medical advice.]"
        ),
    },
    {
        "work_id": "skybrary-pd-pasteur-germ-001",
        "title": {"en": "Germ theory for the public - Pasteur era literacy (PD summary)"},
        "creators": ["Louis Pasteur tradition / public-domain science popularization (curated)"],
        "subjects": ["health_edu", "science", "medicine", "history_pd"],
        "tier": 2,
        "priority_class": "health",
        "summary": {
            "en": "Historical science literacy: microbes and cleanliness - not clinical microbiology."
        },
        "body": (
            "Germ Theory for the Public (Historical Science Literacy)\n\n"
            "IMPORTANT: Educational history of science only. NOT diagnostic lab guidance.\n\n"
            "In the nineteenth century, Pasteur and contemporaries showed that many fermentations "
            "and diseases relate to microscopic life. Public teaching that followed stressed:\n\n"
            "1. Invisible organisms can spoil food and spread illness.\n"
            "2. Heat can kill many microbes (pasteurization of milk became a classic example).\n"
            "3. Cleanliness of instruments and dressings reduces infection risk in care settings.\n"
            "4. Separating sick animals or people when advised can slow outbreaks (quarantine literacy).\n\n"
            "Modern medicine uses vaccines, antibiotics, sterile technique, and laboratory diagnosis "
            "taught by professionals. This text is heritage science literacy for Skybrary kits.\n\n"
            "[Curated educational summary of public-domain science themes. Not medical advice.]"
        ),
    },
    {
        "work_id": "skybrary-pd-quarantine-literacy-001",
        "title": {"en": "Quarantine and isolation literacy (historical public-health summary)"},
        "creators": ["Public-domain epidemic response literature (curated)"],
        "subjects": ["health_edu", "emergency", "safety", "history_pd"],
        "tier": 1,
        "priority_class": "emergency",
        "summary": {
            "en": "Historical community literacy on separating the sick - not a modern outbreak playbook."
        },
        "body": (
            "Quarantine and Isolation Literacy (Historical Summary)\n\n"
            "IMPORTANT: Educational only. Outbreak response is directed by national and WHO guidance. "
            "Do not invent isolation rules that contradict trained authorities.\n\n"
            "Historical public-health writing often distinguished:\n\n"
            "1. Isolation: keeping a sick person away from others when advised, with care for dignity "
            "and basic needs (food, water, clean bedding).\n"
            "2. Quarantine: limiting movement of people who may have been exposed, when ordered by authority.\n"
            "3. Caregiver protection: clean hands, separate utensils when recommended, and rest for helpers.\n"
            "4. Honest information: rumors increase panic; listen to official channels.\n"
            "5. Continuity of essential care: emergency childbirth, trauma, and chronic medicine needs "
            "still require trained workers even during outbreaks.\n\n"
            "SkyCache operators in disaster mode should pair this literacy with local authority sheets "
            "under open licenses when available.\n\n"
            "[Curated educational summary. Skybrary emergency-health pack. Not medical advice.]"
        ),
    },
    {
        "work_id": "skybrary-pd-heat-cold-literacy-001",
        "title": {"en": "Heat and cold exposure literacy (historical field summary)"},
        "creators": ["Public-domain first-aid and field hygiene sources (curated)"],
        "subjects": ["health_edu", "emergency", "safety"],
        "tier": 1,
        "priority_class": "emergency",
        "summary": {
            "en": "Field literacy on heat exhaustion and cold exposure themes - not clinical treatment."
        },
        "body": (
            "Heat and Cold Exposure Literacy (Historical Field Summary)\n\n"
            "IMPORTANT: Educational only. Severe heat stroke and hypothermia are emergencies - "
            "seek trained care. Follow current wilderness and EMS guidance from certified sources.\n\n"
            "Historical field manuals commonly taught community helpers to:\n\n"
            "Heat:\n"
            "- Move the person to shade; loosen tight clothing when safe.\n"
            "- Offer sips of safe water if the person is awake and able to drink.\n"
            "- Cool with wet cloths on skin when water is available; avoid overheating helpers.\n"
            "- Do not force fluids into an unconscious person.\n\n"
            "Cold:\n"
            "- Move out of wind and wet ground when possible; remove wet outer layers if dry clothes exist.\n"
            "- Insulate from the ground; share body warmth carefully without burns.\n"
            "- Offer warm sweet fluids only if fully awake.\n"
            "- Do not rub frostbitten areas with snow (historical warnings against folk harm).\n\n"
            "[Curated educational summary. Skybrary emergency-health pack. Not medical advice.]"
        ),
    },
    {
        "work_id": "skybrary-pd-food-hygiene-001",
        "title": {"en": "Food hygiene literacy (historical household summary)"},
        "creators": ["Public-domain domestic science and sanitation texts (curated)"],
        "subjects": ["health_edu", "safety", "agriculture"],
        "tier": 2,
        "priority_class": "health",
        "summary": {
            "en": "Household food safety literacy themes - not commercial food regulation."
        },
        "body": (
            "Food Hygiene Literacy (Historical Household Summary)\n\n"
            "IMPORTANT: Educational household literacy. NOT food-business certification.\n\n"
            "Public-domain domestic science materials often stressed:\n\n"
            "1. Wash hands before preparing food.\n"
            "2. Keep raw meat separate from ready-to-eat foods when possible.\n"
            "3. Cook thoroughly when fuel allows; reheat leftovers until steaming hot.\n"
            "4. Cover food against flies.\n"
            "5. Use clean utensils and clean water for washing produce when available.\n"
            "6. Discard food that smells rotten or is moldy beyond cultural safe use.\n\n"
            "Market and restaurant rules are set by local inspection authorities.\n\n"
            "[Curated educational summary. Skybrary health pack. Not medical advice.]"
        ),
    },
    {
        "work_id": "skybrary-pd-mosquito-literacy-001",
        "title": {"en": "Mosquito-borne illness literacy (historical community summary)"},
        "creators": ["Public-domain tropical hygiene education (curated)"],
        "subjects": ["health_edu", "emergency", "safety", "medicine"],
        "tier": 1,
        "priority_class": "health",
        "summary": {
            "en": "Community literacy on mosquitoes and standing water - not malaria diagnosis."
        },
        "body": (
            "Mosquito-Borne Illness Literacy (Historical Community Summary)\n\n"
            "IMPORTANT: Educational only. Fever after mosquito exposure needs trained assessment. "
            "Not a substitute for national malaria/dengue programs or laboratory tests.\n\n"
            "Historical tropical hygiene teaching often included:\n\n"
            "1. Mosquitoes breed in standing water - empty or cover containers when practical.\n"
            "2. Sleep under nets when nets are available and intact.\n"
            "3. Seek care early for high fever, confusion, bleeding, or inability to drink.\n"
            "4. Pregnant people and young children are often prioritized by health programs.\n"
            "5. Insecticide and drug programs must follow trained campaign rules - do not improvise chemicals.\n\n"
            "[Curated educational summary. Skybrary health pack. Not medical advice. Not diagnosis.]"
        ),
    },
    {
        "work_id": "skybrary-pd-wound-care-literacy-001",
        "title": {"en": "Simple wound care literacy (historical educational summary)"},
        "creators": ["Public-domain first-aid handbooks (curated)"],
        "subjects": ["health_edu", "emergency", "safety", "medicine"],
        "tier": 1,
        "priority_class": "emergency",
        "summary": {
            "en": "Historical simple wound cleanliness themes - not surgical training."
        },
        "body": (
            "Simple Wound Care Literacy (Historical Educational Summary)\n\n"
            "IMPORTANT: Educational only. Deep, dirty, animal, or heavily bleeding wounds need "
            "trained care. Not tetanus protocol. Not surgical instruction.\n\n"
            "Public-domain first-aid literature commonly taught community helpers to:\n\n"
            "1. Stop severe bleeding with firm direct pressure using the cleanest cloth available.\n"
            "2. Rinse dirt from minor cuts with clean water when available; avoid harsh folk chemicals.\n"
            "3. Cover with a clean dressing; change if soaked or dirty.\n"
            "4. Watch for spreading redness, fever, or pus - seek skilled care.\n"
            "5. Do not close deep wounds with improvised stitching.\n\n"
            "Vaccination and antibiotic decisions belong to licensed clinicians.\n\n"
            "[Curated educational summary. Skybrary emergency-health pack. Not medical advice.]"
        ),
    },
    {
        "work_id": "skybrary-pd-mental-rest-literacy-001",
        "title": {"en": "Rest, grief, and helper stress literacy (historical community summary)"},
        "creators": ["Public-domain nursing and disaster community notes (curated)"],
        "subjects": ["health_edu", "emergency", "safety"],
        "tier": 2,
        "priority_class": "health",
        "summary": {
            "en": "Community dignity literacy for helpers after crisis - not psychotherapy."
        },
        "body": (
            "Rest, Grief, and Helper Stress Literacy (Historical Community Summary)\n\n"
            "IMPORTANT: Educational community dignity themes only. NOT psychotherapy, "
            "NOT psychiatric diagnosis. People in crisis may need trained mental health services.\n\n"
            "Historical nursing and disaster notes often reminded helpers:\n\n"
            "1. Sleep and food for caregivers matter; exhausted helpers make more mistakes.\n"
            "2. Listen without forcing people to tell traumatic details.\n"
            "3. Keep families together when safe; reunification reduces secondary harm.\n"
            "4. Children need predictable routines when possible (meals, rest, play).\n"
            "5. Seek help if a person talks of suicide or cannot care for basic needs - involve professionals.\n\n"
            "[Curated educational summary. Skybrary health pack. Not medical or psychiatric advice.]"
        ),
    },
]
