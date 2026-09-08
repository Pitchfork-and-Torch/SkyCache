"""Skybrary PD wave 4: multilingual humanitarian locales (v1.25).

Arabic, Swahili, Hindi (translit), Japanese (romaji + note) short public-domain
or traditional literacy samples for dual-access catalog. Not a complete archive.
Not free commercial broadband.
"""

from __future__ import annotations

ML2_SAMPLES: list[dict] = [
    {
        "work_id": "skybrary-pd-kalila-ar-001",
        "title": {
            "en": "Kalila and Dimna - the crow and the snake (traditional)",
            "ar": "Kalila wa Dimna (excerpt, traditional)",
        },
        "creators": ["Traditional (Kalila and Dimna tradition)"],
        "languages": ["ar", "en"],
        "subjects": ["literature_pd", "literacy", "fable", "multilingual", "heritage"],
        "tier": 2,
        "priority_class": "education",
        "summary": {
            "en": "Public-domain English retelling of a traditional Kalila and Dimna fable for Arabic-locale literacy demos."
        },
        "body": (
            "Kalila and Dimna - The Crow and the Snake (traditional retelling)\n\n"
            "A crow nested in a tree near a black snake that ate her young. "
            "In grief she asked a jackal for counsel. The jackal said: do not "
            "fight the snake with force; use craft. Scatter jewels from a "
            "nearby palace path so servants follow the trail into the snake's "
            "hole. When they dig for treasure, they will kill the snake.\n\n"
            "The crow did so. The servants found the snake, slew it, and the "
            "crow's nest was safe again.\n\n"
            "Moral (traditional): wisdom and patience outmatch raw strength.\n\n"
            "Note: Arabic script editions may be added by operators under local "
            "open-content rules. This kit ships an English PD-style retelling so "
            "every node can render it without font gaps.\n\n"
            "[Traditional public-domain fable tradition - Skybrary multilingual pack.]"
        ),
    },
    {
        "work_id": "skybrary-pd-swahili-proverbs-001",
        "title": {
            "en": "Swahili proverbs (traditional selection)",
            "sw": "Methali za Kiswahili (uteuzi)",
        },
        "creators": ["Traditional East African proverbs"],
        "languages": ["sw", "en"],
        "subjects": ["literature_pd", "literacy", "heritage", "multilingual"],
        "tier": 2,
        "priority_class": "education",
        "summary": {
            "en": "Traditional Swahili proverbs with English glosses for literacy and village training."
        },
        "body": (
            "Methali za Kiswahili / Swahili proverbs (traditional)\n\n"
            "Haraka haraka haina baraka.\n"
            "  - Haste has no blessing. (Slow careful work beats rush.)\n\n"
            "Unity is strength: kidole kimoja hakivunji chawa.\n"
            "  - One finger cannot kill a louse. (Cooperate.)\n\n"
            "Asiyefunzwa na mamaye hufunzwa na ulimwengu.\n"
            "  - Who is not taught by their mother is taught by the world.\n\n"
            "Mwenye njaa hana miiko.\n"
            "  - The hungry person has no taboos. (Need changes rules carefully.)\n\n"
            "Bandu bandu humaliza gogo.\n"
            "  - Chip by chip finishes the log. (Steady progress.)\n\n"
            "Usisahau mizizi yako.\n"
            "  - Do not forget your roots.\n\n"
            "[Traditional proverbs - public domain oral tradition, curated for Skybrary.]"
        ),
    },
    {
        "work_id": "skybrary-pd-kabir-hi-001",
        "title": {
            "en": "Kabir - selected dohas (public domain tradition)",
            "hi": "Kabir ke dohe (selected)",
        },
        "creators": ["Kabir (traditional public-domain verses)"],
        "languages": ["hi", "en"],
        "subjects": ["literature_pd", "literacy", "poetry", "heritage", "multilingual"],
        "tier": 2,
        "priority_class": "education",
        "summary": {
            "en": "Selected Kabir couplets in ASCII transliteration with English gloss for literacy demos."
        },
        "body": (
            "Kabir - selected dohas (public domain tradition)\n"
            "ASCII transliteration for offline kits\n\n"
            "Bura jo dekhan main chala, bura na milya koi;\n"
            "Jo dil khoja apna, to mujhse bura na koi.\n"
            "  - I set out to find the wicked; found none outside.\n"
            "    Searching my own heart, none was worse than I.\n\n"
            "Pothi padh padh jag mua, pandit bhaya na koi;\n"
            "Dhai akshar prem ka, padhe so pandit hoi.\n"
            "  - Reading stacks of books makes no sage;\n"
            "    two-and-a-half letters of love make the wise.\n\n"
            "Jaise til mein tel hai, jyon chakmak mein aag;\n"
            "Tera sain tujh mein base, jaag sake to jaag.\n"
            "  - Oil is in the sesame; fire is in the flint;\n"
            "    the beloved dwells in you - awaken if you can.\n\n"
            "Note: Devanagari originals are public domain (Kabir tradition). "
            "Operators may replace transliteration with full script locally.\n\n"
            "[Public domain tradition - Skybrary multilingual pack.]"
        ),
    },
    {
        "work_id": "skybrary-pd-basho-ja-001",
        "title": {
            "en": "Matsuo Basho - selected haiku (romaji)",
            "ja": "Basho haiku (selected)",
        },
        "creators": ["Matsuo Basho"],
        "languages": ["ja", "en"],
        "subjects": ["literature_pd", "literacy", "poetry", "heritage", "multilingual"],
        "tier": 2,
        "priority_class": "education",
        "summary": {
            "en": "Public-domain Basho haiku in romaji with English gloss for multilingual poetry literacy."
        },
        "body": (
            "Matsuo Basho - selected haiku (public domain)\n"
            "Romaji + English gloss\n\n"
            "Furu ike ya / kawazu tobikomu / mizu no oto\n"
            "  - Old pond - / a frog jumps in / water's sound\n\n"
            "Natsu-gusa ya / tsuwamono-domo ga / yume no ato\n"
            "  - Summer grasses - / all that remains / of warriors' dreams\n\n"
            "Shizukasa ya / iwa ni shimi-iru / semi no koe\n"
            "  - Stillness - / sinking into the rocks / cicada cry\n\n"
            "Aki fukaki / tonari wa nani o / suru hito zo\n"
            "  - Autumn deepens - / what does my neighbor / do for a living?\n\n"
            "Note: Japanese originals are public domain (Basho d. 1694). "
            "This kit ships romaji so every node can render without CJK fonts. "
            "Operators may install full Japanese text locally.\n\n"
            "[Public domain Japanese poetry - Skybrary multilingual pack.]"
        ),
    },
    {
        "work_id": "skybrary-pd-yoruba-proverbs-001",
        "title": {
            "en": "Yoruba proverbs (traditional selection)",
            "yo": "Owe Yoruba (selected)",
        },
        "creators": ["Traditional Yoruba proverbs"],
        "languages": ["yo", "en"],
        "subjects": ["literature_pd", "literacy", "heritage", "multilingual"],
        "tier": 2,
        "priority_class": "education",
        "summary": {
            "en": "Traditional Yoruba proverbs with English glosses for literacy and community training."
        },
        "body": (
            "Yoruba proverbs / Owe (traditional selection)\n\n"
            "Ile la ti n ko eso r'ode.\n"
            "  - Charity begins at home. (Character starts in the household.)\n\n"
            "Bi a ba n gun'yan, bi a ba n se'be, ise ti a ba fi'wo le a ma dun ni.\n"
            "  - Whatever work you put your hand to, do it well.\n\n"
            "Oju l'oro wa.\n"
            "  - The face carries the message. (Presence and respect matter.)\n\n"
            "Agba ki i wa loja, k'ori omo titun wo.\n"
            "  - When elders are in the market, a child's head is not left crooked.\n"
            "    (Community protects the young.)\n\n"
            "Igi kan ko le da igbo se.\n"
            "  - One tree does not make a forest. (Need many people.)\n\n"
            "[Traditional proverbs - public domain oral tradition, curated for Skybrary.]"
        ),
    },
    {
        "work_id": "skybrary-pd-tagore-bn-001",
        "title": {
            "en": "Tagore - Gitanjali selections (public domain EN)",
            "bn": "Gitanjali (selected EN)",
        },
        "creators": ["Rabindranath Tagore"],
        "languages": ["en", "bn"],
        "subjects": ["literature_pd", "literacy", "poetry", "heritage", "multilingual"],
        "tier": 2,
        "priority_class": "education",
        "summary": {
            "en": "Public-domain English Gitanjali selections (1913 Nobel tradition) for heritage literacy."
        },
        "body": (
            "Gitanjali - selected poems (public domain English)\n"
            "Rabindranath Tagore\n\n"
            "Thou hast made me endless, such is thy pleasure. This frail vessel "
            "thou emptiest again and again, and fillest it ever with fresh life.\n\n"
            "This little flute of a reed thou hast carried over hills and dales, "
            "and hast breathed through it melodies eternally new.\n\n"
            "At the immortal touch of thy hands my little heart loses its limits "
            "in joy and gives birth to utterance ineffable.\n\n"
            "Thy infinite gifts come to me only on these very small hands of mine. "
            "Ages pass, and still thou pourest, and still there is room to fill.\n\n"
            "Where the mind is without fear and the head is held high;\n"
            "Where knowledge is free;\n"
            "Where the world has not been broken up into fragments by narrow domestic walls;\n"
            "Where words come out from the depth of truth;\n"
            "Where tireless striving stretches its arms towards perfection;\n"
            "Where the clear stream of reason has not lost its way into the dreary "
            "desert sand of dead habit;\n"
            "Where the mind is led forward by thee into ever-widening thought and action -\n"
            "Into that heaven of freedom, my Father, let my country awake.\n\n"
            "[Public domain English (Tagore / Macmillan era PD) - Skybrary multilingual pack.]"
        ),
    },
]
