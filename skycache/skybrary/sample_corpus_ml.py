"""Skybrary PD wave 3: multilingual curated public-domain works (v1.24).

Short literacy / heritage samples in non-English languages (with English titles
for the dual-access catalog). Public domain / traditional only.
Not a complete archive. Not free commercial broadband.
"""

from __future__ import annotations

# Multilingual curated public-domain corpus (literacy + heritage)
ML_SAMPLES: list[dict] = [
    {
        "work_id": "skybrary-pd-lafontaine-fr-001",
        "title": {
            "en": "La Cigale et la Fourmi (La Fontaine)",
            "fr": "La Cigale et la Fourmi",
        },
        "creators": ["Jean de La Fontaine"],
        "languages": ["fr"],
        "subjects": ["literature_pd", "literacy", "fable", "multilingual"],
        "tier": 2,
        "priority_class": "education",
        "summary": {
            "en": "Classic French public-domain fable (full short text) for multilingual literacy demos."
        },
        "body": (
            "La Cigale et la Fourmi\n"
            "Jean de La Fontaine\n\n"
            "La Cigale, ayant chante tout l'ete,\n"
            "Se trouva fort depourvue\n"
            "Quand la bise fut venue:\n"
            "Pas un seul petit morceau\n"
            "De mouche ou de vermisseau.\n"
            "Elle alla crier famine\n"
            "Chez la Fourmi sa voisine,\n"
            "La priant de lui preter\n"
            "Quelque grain pour subsister\n"
            "Jusqu'a la saison nouvelle.\n"
            "Je vous paierai, lui dit-elle,\n"
            "Avant l'Aout, foi d'animal,\n"
            "Interet et principal.\n"
            "La Fourmi n'est pas preteuse:\n"
            "C'est la son moindre defaut.\n"
            "Que faisiez-vous au temps chaud?\n"
            "Dit-elle a cette emprunteuse.\n"
            "Nuit et jour a tout venant\n"
            "Je chantais, ne vous deplaise.\n"
            "Vous chantiez? j'en suis fort aise.\n"
            "Eh bien! dansez maintenant.\n\n"
            "[Public domain French - Skybrary multilingual pack.]"
        ),
    },
    {
        "work_id": "skybrary-pd-quijote-es-001",
        "title": {
            "en": "Don Quixote - opening (Cervantes)",
            "es": "Don Quijote - comienzo",
        },
        "creators": ["Miguel de Cervantes"],
        "languages": ["es"],
        "subjects": ["literature_pd", "literacy", "heritage", "multilingual"],
        "tier": 2,
        "priority_class": "education",
        "summary": {
            "en": "Public-domain Spanish opening of Don Quixote for heritage literacy (excerpt)."
        },
        "body": (
            "Don Quijote de la Mancha (comienzo)\n"
            "Miguel de Cervantes Saavedra\n\n"
            "En un lugar de la Mancha, de cuyo nombre no quiero acordarme, "
            "no ha mucho tiempo que vivia un hidalgo de los de lanza en astillero, "
            "adarga antigua, rocin flaco y galgo corredor. Una olla de algo mas vaca "
            "que carnero, salpicon las mas noches, duelos y quebrantos los sabados, "
            "lentejas los viernes, algun palomino de anadidura los domingos, "
            "consumian las tres partes de su hacienda.\n\n"
            "El resto della concluian sayo de velarte, calzas de velludo para las fiestas, "
            "con sus pantuflos de lo mesmo, y los dias de entresemana se honraba con su "
            "vellori de lo mas fino. Tenia en su casa una ama que pasaba de los cuarenta, "
            "y una sobrina que no llegaba a los veinte, y un mozo de campo y plaza, "
            "que asi ensillaba el rocin como tomaba la podadera.\n\n"
            "Frisaba la edad de nuestro hidalgo con los cincuenta anos; era de complexion "
            "recia, seco de carnes, enjuto de rostro, gran madrugador y amigo de la caza.\n\n"
            "[Public domain Spanish - Skybrary multilingual pack. Excerpt only.]"
        ),
    },
    {
        "work_id": "skybrary-pd-dante-it-001",
        "title": {
            "en": "Inferno Canto I opening (Dante)",
            "it": "Inferno, Canto I (inizio)",
        },
        "creators": ["Dante Alighieri"],
        "languages": ["it"],
        "subjects": ["literature_pd", "literacy", "heritage", "multilingual"],
        "tier": 2,
        "priority_class": "education",
        "summary": {
            "en": "Public-domain Italian opening of the Divine Comedy Inferno (short)."
        },
        "body": (
            "La Divina Commedia - Inferno, Canto I (inizio)\n"
            "Dante Alighieri\n\n"
            "Nel mezzo del cammin di nostra vita\n"
            "mi ritrovai per una selva oscura,\n"
            "che la diritta via era smarrita.\n\n"
            "Ahi quanto a dir qual era e cosa dura\n"
            "esta selva selvaggia e aspra e forte\n"
            "che nel pensier rinova la paura!\n\n"
            "Tant' e amara che poco e piu morte;\n"
            "ma per trattar del ben ch'i' vi trovai,\n"
            "diro de l'altre cose ch'i' v'ho scorte.\n\n"
            "Io non so ben ridir com' i' v'intrai,\n"
            "tant' era pien di sonno a quel punto\n"
            "che la verace via abbandonai.\n\n"
            "[Public domain Italian - Skybrary multilingual pack. Excerpt only.]"
        ),
    },
    {
        "work_id": "skybrary-pd-goethe-de-001",
        "title": {
            "en": "Erlkoenig (Goethe)",
            "de": "Erlkoenig",
        },
        "creators": ["Johann Wolfgang von Goethe"],
        "languages": ["de"],
        "subjects": ["literature_pd", "literacy", "poetry", "multilingual"],
        "tier": 2,
        "priority_class": "education",
        "summary": {
            "en": "Full public-domain German ballad for multilingual poetry literacy."
        },
        "body": (
            "Erlkoenig\n"
            "Johann Wolfgang von Goethe\n\n"
            "Wer reitet so spaet durch Nacht und Wind?\n"
            "Es ist der Vater mit seinem Kind;\n"
            "Er hat den Knaben wohl in dem Arm,\n"
            "Er fasst ihn sicher, er haelt ihn warm.\n\n"
            "Mein Sohn, was birgst du so bang dein Gesicht? -\n"
            "Siehst, Vater, du den Erlkoenig nicht?\n"
            "Den Erlenkoenig mit Kron und Schweif? -\n"
            "Mein Sohn, es ist ein Nebelstreif. -\n\n"
            "Du liebes Kind, komm, geh mit mir!\n"
            "Gar schoene Spiele spiel' ich mit dir;\n"
            "Manch' bunte Blumen sind an dem Strand,\n"
            "Meine Mutter hat manch guelden Gewand. -\n\n"
            "Mein Vater, mein Vater, und hoerest du nicht,\n"
            "Was Erlenkoenig mir leise verspricht? -\n"
            "Sei ruhig, bleibe ruhig, mein Kind;\n"
            "In duerren Blaettern saeuselt der Wind. -\n\n"
            "Willst, feiner Knabe, du mit mir gehn?\n"
            "Meine Toechter sollen dich warten schoen;\n"
            "Meine Toechter fuehren den naechtlichen Reihn,\n"
            "Und wiegen und tanzen und singen dich ein. -\n\n"
            "Mein Vater, mein Vater, und siehst du nicht dort\n"
            "Erlkoenigs Toechter am duestern Ort? -\n"
            "Mein Sohn, mein Sohn, ich seh es genau:\n"
            "Es scheinen die alten Weiden so grau. -\n\n"
            "Ich liebe dich, mich reizt deine schoene Gestalt;\n"
            "Und bist du nicht willig, so brauch ich Gewalt. -\n"
            "Mein Vater, mein Vater, jetzt fasst er mich an!\n"
            "Erlkoenig hat mir ein Leids getan! -\n\n"
            "Dem Vater grauset's, er reitet geschwind,\n"
            "Er haelt in Armen das aechzende Kind,\n"
            "Erreicht den Hof mit Muehe und Not;\n"
            "In seinen Armen das Kind war tot.\n\n"
            "[Public domain German - Skybrary multilingual pack.]"
        ),
    },
    {
        "work_id": "skybrary-pd-camoes-pt-001",
        "title": {
            "en": "Os Lusiadas - opening stanza (Camoes)",
            "pt": "Os Lusiadas - estrofe inicial",
        },
        "creators": ["Luis de Camoes"],
        "languages": ["pt"],
        "subjects": ["literature_pd", "literacy", "heritage", "multilingual"],
        "tier": 2,
        "priority_class": "education",
        "summary": {
            "en": "Public-domain Portuguese epic opening (short) for heritage literacy."
        },
        "body": (
            "Os Lusiadas (inicio)\n"
            "Luis de Camoes\n\n"
            "As armas e os baroes assinalados,\n"
            "Que da ocidental praia Lusitana,\n"
            "Por mares nunca de antes navegados,\n"
            "Passaram ainda alem da Taprobana,\n"
            "Em perigos e guerras esforcados,\n"
            "Mais do que prometia a forca humana,\n"
            "E entre gente remota edificaram\n"
            "Novo Reino, que tanto sublimaram;\n\n"
            "E tambem as memorias gloriosas\n"
            "Daqueles Reis, que foram dilatando\n"
            "A Fe, o Imperio, e as terras viciosas\n"
            "De Africa e de Asia andaram devastando;\n"
            "E aqueles, que por obras valerosas\n"
            "Se vao da lei da morte libertando;\n"
            "Cantando espalharei por toda parte,\n"
            "Se a tanto me ajudar o engenho e arte.\n\n"
            "[Public domain Portuguese - Skybrary multilingual pack. Excerpt only.]"
        ),
    },
    {
        "work_id": "skybrary-pd-gaudeamus-la-001",
        "title": {
            "en": "Gaudeamus igitur (traditional Latin)",
            "la": "Gaudeamus igitur",
        },
        "creators": ["Traditional (Latin academic song)"],
        "languages": ["la"],
        "subjects": ["literature_pd", "literacy", "heritage", "multilingual"],
        "tier": 3,
        "priority_class": "education",
        "summary": {
            "en": "Traditional public-domain Latin academic song (selected verses)."
        },
        "body": (
            "Gaudeamus igitur\n"
            "Traditional Latin academic song\n\n"
            "Gaudeamus igitur\n"
            "Iuvenes dum sumus.\n"
            "Post iucundam iuventutem\n"
            "Post molestam senectutem\n"
            "Nos habebit humus.\n\n"
            "Ubi sunt qui ante nos\n"
            "In mundo fuere?\n"
            "Vadite ad superos\n"
            "Transite in inferos\n"
            "Hos si vis videre.\n\n"
            "Vita nostra brevis est\n"
            "Brevi finietur.\n"
            "Venit mors velociter\n"
            "Rapit nos atrociter\n"
            "Nemini parcetur.\n\n"
            "Vivat academia!\n"
            "Vivant professores!\n"
            "Vivat membrum quodlibet;\n"
            "Vivant membra quaelibet;\n"
            "Semper sint in flore.\n\n"
            "[Public domain traditional Latin - Skybrary multilingual pack.]"
        ),
    },
    {
        "work_id": "skybrary-pd-pushkin-ru-001",
        "title": {
            "en": "Ya vas lyubil (Pushkin)",
            "ru": "Ya vas lyubil",
        },
        "creators": ["Alexander Pushkin"],
        "languages": ["ru"],
        "subjects": ["literature_pd", "literacy", "poetry", "multilingual"],
        "tier": 2,
        "priority_class": "education",
        "summary": {
            "en": "Public-domain Russian short poem (transliteration + note) for literacy demos."
        },
        "body": (
            "Ya vas lyubil (I loved you)\n"
            "Alexander Pushkin (public domain)\n\n"
            "Transliterated Russian (for ASCII-safe offline kits):\n\n"
            "Ya vas lyubil: lyubov' eshche, byt' mozhet,\n"
            "V dushe moyei ugasla ne sovsem;\n"
            "No pust' ona vas bol'she ne trevozhit;\n"
            "Ya ne khochu pechalit' vas nichem.\n\n"
            "Ya vas lyubil bezmolvno, beznadezhno,\n"
            "To robost'yu, to revnost'yu tomim;\n"
            "Ya vas lyubil tak iskrenno, tak nezhno,\n"
            "Kak dai vam bog lyubimoi byt' drugim.\n\n"
            "Note: Cyrillic original is public domain (Pushkin d. 1837). "
            "This kit ships an ASCII transliteration so every SkyCache node can render it "
            "without font gaps. Operators may replace with full Cyrillic locally.\n\n"
            "[Public domain Russian (transliteration) - Skybrary multilingual pack.]"
        ),
    },
    {
        "work_id": "skybrary-pd-confucius-zh-001",
        "title": {
            "en": "Analects - selected sayings (traditional)",
            "zh": "Lunyu (selected)",
        },
        "creators": ["Confucian tradition (public domain English)"],
        "languages": ["en", "zh"],
        "subjects": ["literature_pd", "literacy", "civics", "heritage", "multilingual"],
        "tier": 1,
        "priority_class": "education",
        "summary": {
            "en": "Public-domain English selections from the Analects for civics/heritage literacy."
        },
        "body": (
            "The Analects - selected sayings (public domain English)\n"
            "Confucian tradition\n\n"
            "The Master said, To learn and at due times to repeat what one has learnt, "
            "is that not after all a pleasure? That friends should come to one from afar, "
            "is this not after all delightful? To remain unsoured even though one's merits "
            "are unrecognized by others, is that not after all what is expected of a gentleman?\n\n"
            "The Master said, He who by reanimating the Old can gain knowledge of the New "
            "is fit to be a teacher.\n\n"
            "The Master said, When you see someone of worth, think of how you may emulate. "
            "When you see someone unworthy, examine your own character.\n\n"
            "Tzu-kung asked about the true gentleman. The Master said, He does not preach "
            "what he practises till he has practised what he preaches.\n\n"
            "Pinyin titles (ASCII): Lunyu xuan. Full Classical Chinese editions may be "
            "added by operators under local open-content rules.\n\n"
            "[Public domain English tradition - Skybrary multilingual pack. Not a complete Analects.]"
        ),
    },
]
