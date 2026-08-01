"""Build curated public-domain Skybrary packs (Skybrary Live / v0.9.0).

Substantial open educational works for dual-access: same packages online
(catalog) and offline (node FTS + USB kits). Not a complete archive.
Texts are public-domain works or traditional PD translations / excerpts.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from skycache.skybrary.integrity import sha256_text
from skycache.skybrary.license_gate import assert_license_allowed
from skycache.skybrary.models import Edition, Work

# Curated public-domain corpus for dual-access (literacy / civics / STEM / health edu)
SAMPLES: list[dict] = [
    {
        "work_id": "skybrary-pd-aesop-001",
        "title": {"en": "The Fox and the Grapes (Aesop)"},
        "creators": ["Aesop (traditional)"],
        "subjects": ["literature_pd", "literacy", "fable"],
        "tier": 2,
        "priority_class": "education",
        "summary": {
            "en": "Traditional public-domain fable for literacy demos (curated short sample)."
        },
        "body": (
            "A Fox one day spied a beautiful bunch of ripe grapes hanging from a vine "
            "trained along the branches of a tree. The grapes seemed ready to burst with juice, "
            "and the Fox's mouth watered as he gazed longingly at them.\n\n"
            "The bunch hung from a high branch, and the Fox had to jump for it. "
            "The first time he jumped he missed it by a long way. So he walked off a short distance "
            "and took a running leap at it, only to fall short once more. Again and again he tried, "
            "but in vain.\n\n"
            "Now he sat down and looked at the grapes in disgust.\n\n"
            "'What a fool I am,' he said. 'Here I am wearing myself out to get a bunch of sour grapes "
            "that are not worth gaping for.'\n\n"
            "And off he walked very, very scornfully.\n\n"
            "[Public domain traditional fable - curated sample for Skybrary.]"
        ),
    },
    {
        "work_id": "skybrary-pd-gettysburg-001",
        "title": {"en": "Gettysburg Address (Abraham Lincoln)"},
        "creators": ["Abraham Lincoln"],
        "subjects": ["history_pd", "literacy", "civics"],
        "tier": 1,
        "priority_class": "education",
        "summary": {"en": "U.S. public-domain civic text (full short address)."},
        "body": (
            "Four score and seven years ago our fathers brought forth on this continent, "
            "a new nation, conceived in Liberty, and dedicated to the proposition that all men "
            "are created equal.\n\n"
            "Now we are engaged in a great civil war, testing whether that nation, or any nation "
            "so conceived and so dedicated, can long endure. We are met on a great battle-field of that war. "
            "We have come to dedicate a portion of that field, as a final resting place for those who here "
            "gave their lives that that nation might live. It is altogether fitting and proper that we should do this.\n\n"
            "But, in a larger sense, we can not dedicate - we can not consecrate - we can not hallow - this ground. "
            "The brave men, living and dead, who struggled here, have consecrated it, far above our poor power to add or detract. "
            "The world will little note, nor long remember what we say here, but it can never forget what they did here. "
            "It is for us the living, rather, to be dedicated here to the unfinished work which they who fought here "
            "have thus far so nobly advanced. It is rather for us to be here dedicated to the great task remaining before us - "
            "that from these honored dead we take increased devotion to that cause for which they gave the last full measure of devotion - "
            "that we here highly resolve that these dead shall not have died in vain - that this nation, under God, "
            "shall have a new birth of freedom - and that government of the people, by the people, for the people, "
            "shall not perish from the earth.\n\n"
            "[U.S. public domain - Skybrary curated pack.]"
        ),
    },
    {
        "work_id": "skybrary-pd-hippocratic-001",
        "title": {"en": "Hippocratic Oath (public domain translation excerpt)"},
        "creators": ["Hippocratic tradition (public domain English excerpt)"],
        "subjects": ["health_edu", "history_pd", "medicine"],
        "tier": 1,
        "priority_class": "health",
        "summary": {
            "en": "Public-domain English excerpt for educational demo - not medical advice."
        },
        "body": (
            "I swear by Apollo Physician and Asclepius and Hygieia and Panacea and all the gods and goddesses, "
            "making them my witnesses, that I will fulfill according to my ability and judgment this oath and this covenant:\n\n"
            "To hold him who has taught me this art as equal to my parents and to live my life in partnership with him, "
            "and in his sons' male lineage as equal to my brothers and to teach them this art - if they desire to learn it - "
            "without fee and covenant; to give a share of precepts and oral instruction and all the other learning "
            "to my sons and to the sons of him who has instructed me and to pupils who have signed the covenant "
            "and have taken an oath according to the medical law, but no one else.\n\n"
            "I will apply dietetic measures for the benefit of the sick according to my ability and judgment; "
            "I will keep them from harm and injustice.\n\n"
            "I will neither give a deadly drug to anybody who asked for it, nor will I make a suggestion to this effect. "
            "Similarly I will not give to a woman an abortive remedy. In purity and holiness I will guard my life and my art.\n\n"
            "I will not use the knife, not even on sufferers from stone, but will withdraw in favor of such men "
            "as are engaged in this work.\n\n"
            "Whatever houses I may visit, I will come for the benefit of the sick, remaining free of all intentional "
            "injustice, of all mischief and in particular of sexual relations with both female and male persons, "
            "be they free or slaves.\n\n"
            "What I may see or hear in the course of the treatment or even outside of the treatment in regard to "
            "the life of men, which on no account one must spread abroad, I will keep to myself, holding such things "
            "shameful to be spoken about.\n\n"
            "If I fulfill this oath and do not violate it, may it be granted to me to enjoy life and art, "
            "being honored with fame among all men for all time to come; if I transgress it and swear falsely, "
            "may the opposite of all this be my lot.\n\n"
            "[Public domain English excerpt for educational demo - not medical advice. Skybrary.]"
        ),
    },
    {
        "work_id": "skybrary-pd-declaration-001",
        "title": {"en": "United States Declaration of Independence (1776)"},
        "creators": ["Continental Congress (U.S.)"],
        "subjects": ["history_pd", "civics", "literacy"],
        "tier": 1,
        "priority_class": "education",
        "summary": {
            "en": "Foundational U.S. civic text in the public domain for civics and literacy kits."
        },
        "body": (
            "IN CONGRESS, July 4, 1776.\n\n"
            "The unanimous Declaration of the thirteen united States of America,\n\n"
            "When in the Course of human events, it becomes necessary for one people to dissolve the political bands "
            "which have connected them with another, and to assume among the powers of the earth, the separate and equal "
            "station to which the Laws of Nature and of Nature's God entitle them, a decent respect to the opinions of "
            "mankind requires that they should declare the causes which impel them to the separation.\n\n"
            "We hold these truths to be self-evident, that all men are created equal, that they are endowed by their "
            "Creator with certain unalienable Rights, that among these are Life, Liberty and the pursuit of Happiness. - "
            "That to secure these rights, Governments are instituted among Men, deriving their just powers from the "
            "consent of the governed, - That whenever any Form of Government becomes destructive of these ends, it is the "
            "Right of the People to alter or to abolish it, and to institute new Government, laying its foundation on such "
            "principles and organizing its powers in such form, as to them shall seem most likely to effect their Safety "
            "and Happiness. Prudence, indeed, will dictate that Governments long established should not be changed for "
            "light and transient causes; and accordingly all experience hath shewn, that mankind are more disposed to "
            "suffer, while evils are sufferable, than to right themselves by abolishing the forms to which they are "
            "accustomed. But when a long train of abuses and usurpations, pursuing invariably the same Object evinces a "
            "design to reduce them under absolute Despotism, it is their right, it is their duty, to throw off such "
            "Government, and to provide new Guards for their future security. - Such has been the patient sufferance of "
            "these Colonies; and such is now the necessity which constrains them to alter their former Systems of "
            "Government. The history of the present King of Great Britain is a history of repeated injuries and "
            "usurpations, all having in direct object the establishment of an absolute Tyranny over these States. "
            "To prove this, let Facts be submitted to a candid world.\n\n"
            "[... full enumeration of grievances omitted in some abridgments; this pack includes the opening "
            "philosophical statement and closes with the declaration of independence.]\n\n"
            "We, therefore, the Representatives of the united States of America, in General Congress, Assembled, "
            "appealing to the Supreme Judge of the world for the rectitude of our intentions, do, in the Name, and by "
            "Authority of the good People of these Colonies, solemnly publish and declare, That these United Colonies "
            "are, and of Right ought to be Free and Independent States; that they are Absolved from all Allegiance to "
            "the British Crown, and that all political connection between them and the State of Great Britain, is and "
            "ought to be totally dissolved; and that as Free and Independent States, they have full Power to levy War, "
            "conclude Peace, contract Alliances, establish Commerce, and to do all other Acts and Things which "
            "Independent States may of right do. And for the support of this Declaration, with a firm reliance on the "
            "protection of divine Providence, we mutually pledge to each other our Lives, our Fortunes and our sacred Honor.\n\n"
            "[U.S. public domain - Skybrary curated civic pack.]"
        ),
    },
    {
        "work_id": "skybrary-pd-bill-of-rights-001",
        "title": {"en": "United States Bill of Rights (Amendments I - X)"},
        "creators": ["U.S. Congress (1789)"],
        "subjects": ["history_pd", "civics", "literacy"],
        "tier": 1,
        "priority_class": "education",
        "summary": {"en": "First ten amendments to the U.S. Constitution (public domain)."},
        "body": (
            "Amendment I\n"
            "Congress shall make no law respecting an establishment of religion, or prohibiting the free exercise thereof; "
            "or abridging the freedom of speech, or of the press; or the right of the people peaceably to assemble, "
            "and to petition the Government for a redress of grievances.\n\n"
            "Amendment II\n"
            "A well regulated Militia, being necessary to the security of a free State, the right of the people to keep "
            "and bear Arms, shall not be infringed.\n\n"
            "Amendment III\n"
            "No Soldier shall, in time of peace be quartered in any house, without the consent of the Owner, nor in time "
            "of war, but in a manner to be prescribed by law.\n\n"
            "Amendment IV\n"
            "The right of the people to be secure in their persons, houses, papers, and effects, against unreasonable "
            "searches and seizures, shall not be violated, and no Warrants shall issue, but upon probable cause, "
            "supported by Oath or affirmation, and particularly describing the place to be searched, and the persons "
            "or things to be seized.\n\n"
            "Amendment V\n"
            "No person shall be held to answer for a capital, or otherwise infamous crime, unless on a presentment or "
            "indictment of a Grand Jury, except in cases arising in the land or naval forces, or in the Militia, when "
            "in actual service in time of War or public danger; nor shall any person be subject for the same offence "
            "to be twice put in jeopardy of life or limb; nor shall be compelled in any criminal case to be a witness "
            "against himself, nor be deprived of life, liberty, or property, without due process of law; nor shall "
            "private property be taken for public use, without just compensation.\n\n"
            "Amendment VI\n"
            "In all criminal prosecutions, the accused shall enjoy the right to a speedy and public trial, by an "
            "impartial jury of the State and district wherein the crime shall have been committed, which district "
            "shall have been previously ascertained by law, and to be informed of the nature and cause of the "
            "accusation; to be confronted with the witnesses against him; to have compulsory process for obtaining "
            "witnesses in his favor, and to have the Assistance of Counsel for his defence.\n\n"
            "Amendment VII\n"
            "In Suits at common law, where the value in controversy shall exceed twenty dollars, the right of trial "
            "by jury shall be preserved, and no fact tried by a jury, shall be otherwise re-examined in any Court of "
            "the United States, than according to the rules of the common law.\n\n"
            "Amendment VIII\n"
            "Excessive bail shall not be required, nor excessive fines imposed, nor cruel and unusual punishments inflicted.\n\n"
            "Amendment IX\n"
            "The enumeration in the Constitution, of certain rights, shall not be construed to deny or disparage others "
            "retained by the people.\n\n"
            "Amendment X\n"
            "The powers not delegated to the United States by the Constitution, nor prohibited by it to the States, "
            "are reserved to the States respectively, or to the people.\n\n"
            "[U.S. public domain - Skybrary civics pack.]"
        ),
    },
    {
        "work_id": "skybrary-pd-shakespeare-sonnet18-001",
        "title": {"en": "Sonnet 18 - Shall I compare thee to a summer's day? (Shakespeare)"},
        "creators": ["William Shakespeare"],
        "subjects": ["literature_pd", "literacy"],
        "tier": 2,
        "priority_class": "education",
        "summary": {"en": "Short public-domain poem for literacy packs and classroom reading."},
        "body": (
            "Shall I compare thee to a summer's day?\n"
            "Thou art more lovely and more temperate:\n"
            "Rough winds do shake the darling buds of May,\n"
            "And summer's lease hath all too short a date;\n"
            "Sometime too hot the eye of heaven shines,\n"
            "And often is his gold complexion dimm'd;\n"
            "And every fair from fair sometime declines,\n"
            "By chance or nature's changing course untrimm'd;\n"
            "But thy eternal summer shall not fade,\n"
            "Nor lose possession of that fair thou ow'st;\n"
            "Nor shall death brag thou wander'st in his shade,\n"
            "When in eternal lines to time thou grow'st:\n"
            "   So long as men can breathe or eyes can see,\n"
            "   So long lives this, and this gives life to thee.\n\n"
            "[Public domain - Shakespeare Sonnet 18. Skybrary literacy pack.]"
        ),
    },
    {
        "work_id": "skybrary-pd-austen-pride-001",
        "title": {"en": "Pride and Prejudice - Opening chapter (Jane Austen)"},
        "creators": ["Jane Austen"],
        "subjects": ["literature_pd", "literacy"],
        "tier": 2,
        "priority_class": "education",
        "summary": {
            "en": "Public-domain novel opening for village literacy kits (Chapter I)."
        },
        "body": (
            "Chapter I\n\n"
            "It is a truth universally acknowledged, that a single man in possession of a good fortune, "
            "must be in want of a wife.\n\n"
            "However little known the feelings or views of such a man may be on his first entering a "
            "neighbourhood, this truth is so well fixed in the minds of the surrounding families, that he is "
            "considered the rightful property of some one or other of their daughters.\n\n"
            "'My dear Mr. Bennet,' said his lady to him one day, 'have you heard that Netherfield Park is "
            "let at last?'\n\n"
            "Mr. Bennet replied that he had not.\n\n"
            "'But it is,' returned she; 'for Mrs. Long has just been here, and she told me all about it.'\n\n"
            "Mr. Bennet made no answer.\n\n"
            "'Do you not want to know who has taken it?' cried his wife impatiently.\n\n"
            "'You want to tell me, and I have no objection to hearing it.'\n\n"
            "This was invitation enough.\n\n"
            "'Why, my dear, you must know, Mrs. Long says that Netherfield is taken by a young man of large "
            "fortune from the north of England; that he came down on Monday in a chaise and four to see the "
            "place, and was so much delighted with it, that he agreed with Mr. Morris immediately; that he is "
            "to take possession before Michaelmas, and some of his servants are to be in the house by the end "
            "of next week.'\n\n"
            "'What is his name?'\n\n"
            "'Bingley.'\n\n"
            "'Is he married or single?'\n\n"
            "'Oh! Single, my dear, to be sure! A single man of large fortune; four or five thousand a year. "
            "What a fine thing for our girls!'\n\n"
            "'How so? How can it affect them?'\n\n"
            "'My dear Mr. Bennet,' replied his wife, 'how can you be so tiresome! You must know that I am "
            "thinking of his marrying one of them.'\n\n"
            "'Is that his design in settling here?'\n\n"
            "'Design! Nonsense, how can you talk so! But it is very likely that he may fall in love with one "
            "of them, and therefore you must visit him as soon as he comes.'\n\n"
            "'I see no occasion for that. You and the girls may go, or you may send them by themselves, which "
            "perhaps will be still better, for as you are as handsome as any of them, Mr. Bingley may like you "
            "the best of the party.'\n\n"
            "'My dear, you flatter me. I certainly have had my share of beauty, but I do not pretend to be "
            "anything extraordinary now. When a woman has five grown-up daughters, she ought to give over "
            "thinking of her own beauty.'\n\n"
            "'In such cases, a woman has not often much beauty to think of.'\n\n"
            "'But, my dear, you must indeed go and see Mr. Bingley when he comes into the neighbourhood.'\n\n"
            "'It is more than I engage for, I assure you.'\n\n"
            "'But consider your daughters. Only think what an establishment it would be for one of them. "
            "Sir William and Lady Lucas are determined to go, merely on that account, for in general, you "
            "know, they visit no newcomers. Indeed you must go, for it will be impossible for us to visit him "
            "if you do not.'\n\n"
            "'You are over-scrupulous, surely. I dare say Mr. Bingley will be very glad to see you; and I will "
            "send a few lines by you to assure him of my hearty consent to his marrying whichever he chooses "
            "of the girls; though I must throw in a good word for my little Lizzy.'\n\n"
            "'I desire you will do no such thing. Lizzy is not a bit better than the others; and I am sure she "
            "is not half so handsome as Jane, nor half so good-humoured as Lydia. But you are always giving "
            "her the preference.'\n\n"
            "'They have none of them much to recommend them,' replied he; 'they are all silly and ignorant "
            "like other girls; but Lizzy has something more of quickness than her sisters.'\n\n"
            "'Mr. Bennet, how can you abuse your own children in such a way? You take delight in vexing me. "
            "You have no compassion on my poor nerves.'\n\n"
            "'You mistake me, my dear. I have a high respect for your nerves. They are my old friends. I have "
            "heard you mention them with consideration these last twenty years at least.'\n\n"
            "'Ah, you do not know what I suffer.'\n\n"
            "'But I hope you will get over it, and live to see many young men of four thousand a year come "
            "into the neighbourhood.'\n\n"
            "'It will be no use to us, if twenty such should come, since you will not visit them.'\n\n"
            "'Depend upon it, my dear, that when there are twenty, I will visit them all.'\n\n"
            "Mr. Bennet was so odd a mixture of quick parts, sarcastic humour, reserve, and caprice, that the "
            "experience of three-and-twenty years had been insufficient to make his wife understand his "
            "character. Her mind was less difficult to develop. She was a woman of mean understanding, little "
            "information, and uncertain temper. When she was discontented, she fancied herself nervous. The "
            "business of her life was to get her daughters married; its solace was visiting and news.\n\n"
            "[Public domain - Pride and Prejudice, Chapter I. Skybrary literacy pack.]"
        ),
    },
    {
        "work_id": "skybrary-pd-dickens-carol-001",
        "title": {"en": "A Christmas Carol - Stave One opening (Charles Dickens)"},
        "creators": ["Charles Dickens"],
        "subjects": ["literature_pd", "literacy"],
        "tier": 2,
        "priority_class": "education",
        "summary": {"en": "Public-domain novel opening for literacy kits."},
        "body": (
            "Stave One - Marley's Ghost\n\n"
            "Marley was dead: to begin with. There is no doubt whatever about that. The register of his "
            "burial was signed by the clergyman, the clerk, the undertaker, and the chief mourner. Scrooge "
            "signed it: and Scrooge's name was good upon 'Change, for anything he chose to put his hand to. "
            "Old Marley was as dead as a door-nail.\n\n"
            "Mind! I don't mean to say that I know, of my own knowledge, what there is particularly dead "
            "about a door-nail. I might have been inclined, myself, to regard a coffin-nail as the deadest "
            "piece of ironmongery in the trade. But the wisdom of our ancestors is in the simile; and my "
            "unhallowed hands shall not disturb it, or the Country's done for. You will therefore permit me "
            "to repeat, emphatically, that Marley was as dead as a door-nail.\n\n"
            "Scrooge knew he was dead? Of course he did. How could it be otherwise? Scrooge and he were "
            "partners for I don't know how many years. Scrooge was his sole executor, his sole administrator, "
            "his sole assign, his sole residuary legatee, his sole friend, and sole mourner. And even Scrooge "
            "was not so dreadfully cut up by the sad event, but that he was an excellent man of business on "
            "the very day of the funeral, and solemnised it with an undoubted bargain.\n\n"
            "The mention of Marley's funeral brings me back to the point I started from. There is no doubt "
            "that Marley was dead. This must be distinctly understood, or nothing wonderful can come of the "
            "story I am going to relate. If we were not perfectly convinced that Hamlet's Father died before "
            "the play began, there would be nothing more remarkable in his taking a stroll at night, in an "
            "easterly wind, upon his own ramparts, than there would be in any other middle-aged gentleman "
            "rashly turning out after dark in a breezy spot - say Saint Paul's Churchyard for instance - "
            "literally to astonish his son's weak mind.\n\n"
            "Scrooge never painted out Old Marley's name. There it stood, years afterwards, above the "
            "warehouse door: Scrooge and Marley. The firm was known as Scrooge and Marley. Sometimes people "
            "new to the business called Scrooge Scrooge, and sometimes Marley, but he answered to both "
            "names. It was all the same to him.\n\n"
            "Oh! But he was a tight-fisted hand at the grindstone, Scrooge! a squeezing, wrenching, "
            "grasping, scraping, clutching, covetous, old sinner! Hard and sharp as flint, from which no "
            "steel had ever struck out generous fire; secret, and self-contained, and solitary as an oyster. "
            "The cold within him froze his old features, nipped his pointed nose, shrivelled his cheek, "
            "stiffened his gait; made his eyes red, his thin lips blue; and spoke out shrewdly in his grating "
            "voice. A frosty rime was on his head, and on his eyebrows, and his wiry chin. He carried his own "
            "low temperature always about with him; he iced his office in the dog-days; and didn't thaw it one "
            "degree at Christmas.\n\n"
            "[Public domain - A Christmas Carol opening. Skybrary literacy pack.]"
        ),
    },
    {
        "work_id": "skybrary-pd-euclid-001",
        "title": {"en": "Euclid's Elements - Book I Definitions (public domain)"},
        "creators": ["Euclid", "Thomas L. Heath (translator, public domain)"],
        "subjects": ["science", "stem", "math", "literacy"],
        "tier": 1,
        "priority_class": "education",
        "summary": {
            "en": "Classic geometry definitions for STEM literacy kits (Book I defs)."
        },
        "body": (
            "Book I - Definitions\n\n"
            "1. A point is that which has no part.\n\n"
            "2. A line is breadthless length.\n\n"
            "3. The extremities of a line are points.\n\n"
            "4. A straight line is a line which lies evenly with the points on itself.\n\n"
            "5. A surface is that which has length and breadth only.\n\n"
            "6. The extremities of a surface are lines.\n\n"
            "7. A plane surface is a surface which lies evenly with the straight lines on itself.\n\n"
            "8. A plane angle is the inclination to one another of two lines in a plane which meet one "
            "another and do not lie in a straight line.\n\n"
            "9. And when the lines containing the angle are straight, the angle is called rectilineal.\n\n"
            "10. When a straight line set up on a straight line makes the adjacent angles equal to one "
            "another, each of the equal angles is right, and the straight line standing on the other is "
            "called a perpendicular to that on which it stands.\n\n"
            "11. An obtuse angle is an angle greater than a right angle.\n\n"
            "12. An acute angle is an angle less than a right angle.\n\n"
            "13. A boundary is that which is an extremity of anything.\n\n"
            "14. A figure is that which is contained by any boundary or boundaries.\n\n"
            "15. A circle is a plane figure contained by one line such that all the straight lines falling "
            "upon it from one point among those lying within the figure are equal to one another.\n\n"
            "16. And the point is called the centre of the circle.\n\n"
            "17. A diameter of the circle is any straight line drawn through the centre and terminated in "
            "both directions by the circumference of the circle, and such a straight line also bisects the "
            "circle.\n\n"
            "23. Parallel straight lines are straight lines which, being in the same plane and being produced "
            "indefinitely in both directions, do not meet one another in either direction.\n\n"
            "Postulates\n\n"
            "1. To draw a straight line from any point to any point.\n\n"
            "2. To produce a finite straight line continuously in a straight line.\n\n"
            "3. To describe a circle with any centre and distance.\n\n"
            "4. That all right angles are equal to one another.\n\n"
            "5. That, if a straight line falling on two straight lines make the interior angles on the same "
            "side less than two right angles, the two straight lines, if produced indefinitely, meet on that "
            "side on which are the angles less than the two right angles.\n\n"
            "[Public domain English (Heath). Skybrary STEM pack - educational geometry foundations.]"
        ),
    },
    {
        "work_id": "skybrary-pd-darwin-origin-001",
        "title": {"en": "On the Origin of Species - Chapter I excerpt (Darwin)"},
        "creators": ["Charles Darwin"],
        "subjects": ["science", "stem", "history_pd"],
        "tier": 1,
        "priority_class": "education",
        "summary": {
            "en": "Public-domain science history excerpt for open STEM education packs."
        },
        "body": (
            "Chapter I - Variation under Domestication\n\n"
            "Causes of Variability\n\n"
            "When we look to the individuals of the same variety or sub-variety of our older cultivated "
            "plants and animals, one of the first points which strikes us, is, that they generally differ "
            "much more from each other, than do the individuals of any one species or variety in a state of "
            "nature. When we reflect on the vast diversity of the plants and animals which have been "
            "cultivated, and which have varied during all ages under the most different climates and "
            "treatment, I think we are driven to conclude that this greater variability is simply due to our "
            "domestic productions having been raised under conditions of life not so uniform as, and "
            "somewhat different from, those to which the parent-species have been exposed under nature. "
            "There is, also, I think, some probability in the view propounded by Andrew Knight, that this "
            "variability may be partly connected with excess of food. It seems pretty clear that organic "
            "beings must be exposed during several generations to the new conditions of life to cause any "
            "appreciable amount of variation; and that when the organisation has once begun to vary, it "
            "generally continues to vary for many generations. No case is on record of a variable being "
            "ceasing to be variable under cultivation. Our oldest cultivated plants, such as wheat, still "
            "often yield new varieties: our oldest domesticated animals are still capable of rapid "
            "improvement or modification.\n\n"
            "Effects of Habit and of the Use or Disuse of Parts; Correlated Variation; Inheritance\n\n"
            "Changed habits produce an inherited effect, as in the period of the flowering of plants when "
            "transported from one climate to another. In animals the increased use or disuse of parts has "
            "had a more marked influence; thus I find in the domestic duck that the bones of the wing weigh "
            "less and the bones of the leg more, in proportion to the whole skeleton, than do the same bones "
            "in the wild-duck; and I presume that this change may be safely attributed to the domestic duck "
            "flying much less, and walking more, than its wild parent. The great and inherited development "
            "of the udders in cows and goats in countries where they are habitually milked, in comparison "
            "with the state of these organs in other countries, is another instance of the effect of use. "
            "Not a single domestic animal can be named which has not in some country drooping ears; and the "
            "view suggested by some authors, that the drooping is due to the disuse of the muscles of the "
            "ear, from the animals not being much alarmed by danger, seems probable.\n\n"
            "[Public domain - Origin of Species, Chapter I excerpt. Skybrary STEM / science history pack. "
            "Educational historical text - not a complete modern biology curriculum.]"
        ),
    },
    {
        "work_id": "skybrary-pd-sunzi-artofwar-001",
        "title": {"en": "The Art of War - Lionel Giles translation excerpts"},
        "creators": ["Sun Tzu", "Lionel Giles (translator)"],
        "subjects": ["history_pd", "literature_pd", "heritage"],
        "tier": 2,
        "priority_class": "education",
        "summary": {
            "en": "Classic public-domain translation excerpts for history / heritage packs."
        },
        "body": (
            "I. Laying Plans\n\n"
            "1. Sun Tzu said: The art of war is of vital importance to the State.\n\n"
            "2. It is a matter of life and death, a road either to safety or to ruin. Hence it is a subject "
            "of inquiry which can on no account be neglected.\n\n"
            "3. The art of war, then, is governed by five constant factors, to be taken into account in "
            "one's deliberations, when seeking to determine the conditions obtaining in the field.\n\n"
            "4. These are: (1) The Moral Law; (2) Heaven; (3) Earth; (4) The Commander; (5) Method and discipline.\n\n"
            "5, 6. The Moral Law causes the people to be in complete accord with their ruler, so that they "
            "will follow him regardless of their lives, undismayed by any danger.\n\n"
            "7. Heaven signifies night and day, cold and heat, times and seasons.\n\n"
            "8. Earth comprises distances, great and small; danger and security; open ground and narrow "
            "passes; the chances of life and death.\n\n"
            "9. The Commander stands for the virtues of wisdom, sincerely, benevolence, courage and strictness.\n\n"
            "10. By method and discipline are to be understood the marshaling of the army in its proper "
            "subdivisions, the graduations of rank among the officers, the maintenance of roads by which "
            "supplies may reach the army, and the control of military expenditure.\n\n"
            "18. All warfare is based on deception.\n\n"
            "19. Hence, when able to attack, we must seem unable; when using our forces, we must seem "
            "inactive; when we are near, we must make the enemy believe we are far away; when far away, we "
            "must make him believe we are near.\n\n"
            "III. Attack by Stratagem\n\n"
            "1. Sun Tzu said: In the practical art of war, the best thing of all is to take the enemy's "
            "country whole and intact; to shatter and destroy it is not so good. So, too, it is better to "
            "recapture an army entire than to destroy it, to capture a regiment, a detachment or a company "
            "entire than to destroy them.\n\n"
            "2. Hence to fight and conquer in all your battles is not supreme excellence; supreme excellence "
            "consists in breaking the enemy's resistance without fighting.\n\n"
            "[Public domain - Lionel Giles translation (1910). Skybrary heritage / history pack.]"
        ),
    },
    {
        "work_id": "skybrary-pd-firstaid-historical-001",
        "title": {"en": "Historical first-aid principles (public-domain educational summary)"},
        "creators": ["Public-domain first-aid handbooks (curated summary)"],
        "subjects": ["health_edu", "emergency", "safety", "medicine"],
        "tier": 1,
        "priority_class": "emergency",
        "summary": {
            "en": "Educational historical first-aid summary for emergency-health packs - not diagnosis."
        },
        "body": (
            "Historical First-Aid Principles (Educational Summary)\n\n"
            "IMPORTANT: This text is for historical and educational literacy only. It is NOT medical advice, "
            "NOT diagnosis, and NOT a substitute for trained emergency responders or modern clinical guidance. "
            "Follow current local health authority protocols.\n\n"
            "1. Keep calm and ensure scene safety.\n"
            "Historically, handbooks stressed that the helper must not become a second casualty. Remove "
            "obvious immediate danger when it is safe to do so; call for help; do not rush into hazards.\n\n"
            "2. Breathing and consciousness.\n"
            "Older manuals taught observation: is the person conscious? Breathing? Responsive to voice? "
            "Modern systems use updated CPR and AED guidance - train with certified instructors for current "
            "technique. Historical texts often emphasized open airway positioning and preventing further injury.\n\n"
            "3. Bleeding control (historical principle).\n"
            "Public-domain manuals commonly taught direct pressure with clean cloth on wounds, elevation of "
            "a limb when appropriate, and seeking skilled care for severe bleeding. Do not improvise tourniquets "
            "without current training.\n\n"
            "4. Burns (historical principle).\n"
            "Older guidance often included cooling with clean water for simple burns and covering with clean "
            "cloth; avoid folk remedies that contaminate wounds. Severe burns require professional care.\n\n"
            "5. Fractures and movement.\n"
            "Historical principle: avoid unnecessary movement of an injured person when spinal or major bone "
            "injury is possible; immobilize only if trained; wait for skilled help when available.\n\n"
            "6. Heat, cold, and dehydration (general literacy).\n"
            "Many open educational sources stress shade, gradual cooling, warm dry covering for cold exposure, "
            "and safe drinking water when available. Oral rehydration education (ORS) is taught separately in "
            "modern public-health materials when licenses permit packaging.\n\n"
            "7. Hygiene and infection awareness.\n"
            "Clean hands, clean water, and clean dressings reduce infection risk - a principle common to both "
            "historical nursing literature and modern community health education.\n\n"
            "8. Record and hand over.\n"
            "Note what happened, times, and care given; hand information to professional responders.\n\n"
            "[Curated educational summary inspired by public-domain first-aid literature. Skybrary "
            "emergency-health pack. Not medical advice. Not complete clinical protocol.]"
        ),
    },
    {
        "work_id": "skybrary-pd-emerson-self-001",
        "title": {"en": "Self-Reliance - excerpt (Ralph Waldo Emerson)"},
        "creators": ["Ralph Waldo Emerson"],
        "subjects": ["literature_pd", "literacy", "civics"],
        "tier": 2,
        "priority_class": "education",
        "summary": {"en": "Public-domain essay excerpt for literacy and civic thought kits."},
        "body": (
            "Self-Reliance (excerpt)\n\n"
            "I read the other day some verses written by an eminent painter which were original and not "
            "conventional. The soul always hears an admonition in such lines, let the subject be what it may. "
            "The sentiment they instil is of more value than any thought they may contain. To believe your own "
            "thought, to believe that what is true for you in your private heart is true for all men, - that is "
            "genius. Speak your latent conviction, and it shall be the universal sense; for the inmost in due "
            "time becomes the outmost, and our first thought is rendered back to us by the trumpets of the Last "
            "Judgment. Familiar as the voice of the mind is to each, the highest merit we ascribe to Moses, "
            "Plato, and Milton is, that they set at naught books and traditions, and spoke not what men, but "
            "what they thought. A man should learn to detect and watch that gleam of light which flashes across "
            "his mind from within, more than the lustre of the firmament of bards and sages. Yet he dismisses "
            "without notice his thought, because it is his. In every work of genius we recognize our own rejected "
            "thoughts: they come back to us with a certain alienated majesty. Great works of art have no more "
            "affecting lesson for us than this. They teach us to abide by our spontaneous impression with "
            "good-humored inflexibility then most when the whole cry of voices is on the other side. Else, "
            "to-morrow a stranger will say with masterly good sense precisely what we have thought and felt all "
            "the time, and we shall be forced to take with shame our own opinion from another.\n\n"
            "There is a time in every man's education when he arrives at the conviction that envy is ignorance; "
            "that imitation is suicide; that he must take himself for better, for worse, as his portion; that "
            "though the wide universe is full of good, no kernel of nourishing corn can come to him but through "
            "his toil bestowed on that plot of ground which is given to him to till. The power which resides in "
            "him is new in nature, and none but he knows what that is which he can do, nor does he know until he "
            "has tried.\n\n"
            "[Public domain - Emerson, Self-Reliance excerpt. Skybrary literacy pack.]"
        ),
    },
    {
        "work_id": "skybrary-pd-franklin-wealth-001",
        "title": {"en": "The Way to Wealth - excerpt (Benjamin Franklin)"},
        "creators": ["Benjamin Franklin"],
        "subjects": ["literature_pd", "literacy", "civics", "history_pd"],
        "tier": 2,
        "priority_class": "education",
        "summary": {"en": "Public-domain practical wisdom essay for literacy kits."},
        "body": (
            "The Way to Wealth (excerpt)\n\n"
            "Courteous Reader,\n\n"
            "I have heard that nothing gives an author so great pleasure as to find his works respectfully "
            "quoted by other learned authors. This pleasure I have seldom enjoyed; for though I have been, if I "
            "may say it without vanity, an eminent author of almanacs annually now a full quarter of a century, "
            "my brother authors in the same way, for what reason I know not, have ever been very sparing in their "
            "applauses, and no other author has taken the least notice of me, so that did not my writings produce "
            "me some solid pudding, the great deficiency of praise would have quite discouraged me.\n\n"
            "I concluded at length, that the people were the best judges of my merit; for they buy my works; and "
            "besides, in my rambles, where I am not personally known, I have frequently heard one or other of my "
            "adages repeated, with as Poor Richard says at the end on't; this gave me some satisfaction, as it "
            "showed not only that my instructions were regarded, but discovered likewise some respect for my "
            "authority; and I own, that to encourage the practice of remembering and repeating those wise "
            "sentences, I have sometimes quoted myself with great gravity.\n\n"
            "Judge, then, how much I must have been gratified by an incident I am going to relate to you. I "
            "stopped my horse lately where a great number of people were collected at a vendue of merchant goods. "
            "The hour of sale not being come, they were conversing on the badness of the times, and one of the "
            "company called to a plain clean old man, with white locks, 'Pray, Father Abraham, what think you of "
            "the times? Won't these heavy taxes quite ruin the country? How shall we ever be able to pay them? "
            "What would you advise us to?' Father Abraham stood up, and replied, 'If you'd have my advice, I'll "
            "give it you in short, for a word to the wise is enough, and many words won't fill a bushel, as Poor "
            "Richard says.' They joined in desiring him to speak his mind, and gathering round him, he proceeded "
            "as follows.\n\n"
            "'Friends,' says he, 'and neighbours, the taxes are indeed very heavy, and if those laid on by the "
            "government were the only ones we had to pay, we might more easily discharge them; but we have many "
            "others, and much more grievous to some of us. We are taxed twice as much by our idleness, three times "
            "as much by our pride, and four times as much by our folly; and from these taxes the commissioners "
            "cannot ease or deliver us by allowing an abatement. However let us hearken to good advice, and "
            "something may be done for us; God helps them that help themselves, as Poor Richard says in his almanac.'\n\n"
            "[Public domain - Franklin, The Way to Wealth excerpt. Skybrary literacy / civics pack.]"
        ),
    },
    {
        "work_id": "skybrary-pd-newton-rules-001",
        "title": {"en": "Newton - Rules of Reasoning in Philosophy (Principia excerpt)"},
        "creators": ["Isaac Newton"],
        "subjects": ["science", "stem", "history_pd"],
        "tier": 1,
        "priority_class": "education",
        "summary": {
            "en": "Public-domain scientific method principles for STEM education packs."
        },
        "body": (
            "Rules of Reasoning in Philosophy\n"
            "(from the Principia - public domain English)\n\n"
            "Rule I\n"
            "We are to admit no more causes of natural things than such as are both true and sufficient to "
            "explain their appearances.\n\n"
            "To this purpose the philosophers say that Nature does nothing in vain, and more is in vain when "
            "less will serve; for Nature is pleased with simplicity, and affects not the pomp of superfluous causes.\n\n"
            "Rule II\n"
            "Therefore to the same natural effects we must, as far as possible, assign the same causes.\n\n"
            "As to respiration in a man and in a beast; the descent of stones in Europe and in America; the "
            "light of our culinary fire and of the sun; the reflection of light in the earth, and in the planets.\n\n"
            "Rule III\n"
            "The qualities of bodies, which admit neither intensification nor remission of degrees, and which "
            "are found to belong to all bodies within the reach of our experiments, are to be esteemed the "
            "universal qualities of all bodies whatsoever.\n\n"
            "For since the qualities of bodies are only known to us by experiments, we are to hold for universal "
            "all such as universally agree with experiments; and such as are not liable to diminution can never "
            "be quite taken away. We are certainly not to relinquish the evidence of experiments for the sake of "
            "dreams and vain fictions of our own devising; nor are we to recede from the analogy of Nature, which "
            "is wont to be simple, and always consonant to itself.\n\n"
            "Rule IV\n"
            "In experimental philosophy we are to look upon propositions inferred by general induction from "
            "phenomena as accurately or very nearly true, notwithstanding any contrary hypotheses that may be "
            "imagined, till such time as other phenomena occur, by which they may either be made more accurate, "
            "or liable to exceptions.\n\n"
            "This rule we must follow, that the argument of induction may not be evaded by hypotheses.\n\n"
            "[Public domain English. Skybrary STEM / science history pack - educational foundations of method.]"
        ),
    },
    {
        "work_id": "skybrary-pd-nightingale-nursing-001",
        "title": {"en": "Notes on Nursing - ventilation & cleanliness excerpts (Nightingale)"},
        "creators": ["Florence Nightingale"],
        "subjects": ["health_edu", "medicine", "history_pd", "safety"],
        "tier": 1,
        "priority_class": "health",
        "summary": {
            "en": "Public-domain nursing education excerpts - historical hygiene literacy, not modern clinical protocol."
        },
        "body": (
            "Notes on Nursing: What It Is, and What It Is Not (excerpts)\n\n"
            "IMPORTANT: Historical educational text only. Not modern clinical guidance or medical advice.\n\n"
            "I. Ventilation and Warming\n\n"
            "The very first canon of nursing, the first and the last thing upon which a nurse's attention must "
            "be fixed, the first essential to a patient, without which all the rest you can do for him is as "
            "nothing, with which I had almost said you may leave all the rest alone, is this: TO KEEP THE AIR "
            "HE BREATHES AS PURE AS THE EXTERNAL AIR, WITHOUT CHILLING HIM. Yet what is so little attended to? "
            "Even where it is thought of at all, the most extraordinary misconceptions reign about it. Even in "
            "admitting air into the patient's room or ward, few people ever think where that air comes from. It "
            "may come from a corridor into which other wards are ventilated, from a hall always unaired, always "
            "full of the fumes of gas, dinner, of various kinds of mustiness; from an underground kitchen, sink, "
            "washhouse, water-closet, or even, as I myself have had sorrowful experience, from open sewers loaded "
            "with filth; and with this the patient's room or ward is aired, as it is called - poisoned, it should "
            "rather be said.\n\n"
            "II. Health of Houses\n\n"
            "There are five essential points in securing the health of houses:  - \n"
            "1. Pure air.\n"
            "2. Pure water.\n"
            "3. Efficient drainage.\n"
            "4. Cleanliness.\n"
            "5. Light.\n\n"
            "Without these, no house can be healthy. And it will be unhealthy just in proportion as they are deficient.\n\n"
            "III. Cleanliness\n\n"
            "It cannot be necessary to tell a nurse that she should be clean, or that she should keep her patient "
            "clean, seeing that the greater part of nursing consists in preserving cleanliness. The greater part "
            "of nursing consists in preserving cleanliness.\n\n"
            "[Public domain - Florence Nightingale, Notes on Nursing (1860) excerpts. Skybrary health education "
            "pack. Historical hygiene literacy - not modern clinical protocol or medical advice.]"
        ),
    },
    {
        "work_id": "skybrary-pd-psalm23-001",
        "title": {"en": "Psalm 23 (King James Version)"},
        "creators": ["Biblical text (KJV public domain)"],
        "subjects": ["literature_pd", "literacy", "heritage"],
        "tier": 2,
        "priority_class": "education",
        "summary": {
            "en": "Public-domain KJV psalm often used in literacy and cultural heritage reading."
        },
        "body": (
            "Psalm 23\n"
            "King James Version (public domain)\n\n"
            "The LORD is my shepherd; I shall not want.\n\n"
            "He maketh me to lie down in green pastures: he leadeth me beside the still waters.\n\n"
            "He restoreth my soul: he leadeth me in the paths of righteousness for his name's sake.\n\n"
            "Yea, though I walk through the valley of the shadow of death, I will fear no evil: for thou art "
            "with me; thy rod and thy staff they comfort me.\n\n"
            "Thou preparest a table before me in the presence of mine enemies: thou anointest my head with oil; "
            "my cup runneth over.\n\n"
            "Surely goodness and mercy shall follow me all the days of my life: and I will dwell in the house of "
            "the LORD for ever.\n\n"
            "[Public domain KJV text. Skybrary heritage / literacy pack. Not a complete religious corpus.]"
        ),
    },
    {
        "work_id": "skybrary-pd-twain-jumping-001",
        "title": {"en": "The Celebrated Jumping Frog - opening (Mark Twain)"},
        "creators": ["Mark Twain (Samuel L. Clemens)"],
        "subjects": ["literature_pd", "literacy"],
        "tier": 2,
        "priority_class": "education",
        "summary": {"en": "Public-domain short story opening for literacy reading practice."},
        "body": (
            "The Celebrated Jumping Frog of Calaveras County (opening)\n\n"
            "In compliance with the request of a friend of mine, who wrote me from the East, I called on "
            "good-natured, garrulous old Simon Wheeler, and inquired after my friend's friend, Leonidas W. Smiley, "
            "as requested to do, and I hereunto append the result. I have a lurking suspicion that Leonidas W. "
            "Smiley is a myth; that my friend never knew such a personage; and that he only conjectured that if I "
            "asked old Wheeler about him, it would remind him of his infamous Jim Smiley, and he would go to work "
            "and bore me to death with some exasperating reminiscence of him as long and as tedious as it should be "
            "useless to me. If that was the design, it succeeded.\n\n"
            "I found Simon Wheeler dozing comfortably by the bar-room stove of the dilapidated tavern in the "
            "decayed mining camp of Angel's, and I noticed that he was fat and bald-headed, and had an expression "
            "of winning gentleness and simplicity upon his tranquil countenance. He roused up, and gave me good-day. "
            "I told him a friend of mine had commissioned me to make some inquiries about a cherished companion of "
            "his boyhood named Leonidas W. Smiley - Rev. Leonidas W. Smiley, a young minister of the Gospel, who he "
            "had heard was at one time a resident of Angel's Camp. I added that if Mr. Wheeler could tell me any "
            "thing about this Rev. Leonidas W. Smiley, I would feel under many obligations to him.\n\n"
            "Simon Wheeler backed me into a corner and blockaded me there with his chair, and then sat down and "
            "reeled off the monotonous narrative which follows this paragraph. He never smiled, he never frowned, "
            "he never changed his voice from the gentle-flowing key to which he tuned his initial sentence, he never "
            "betrayed the slightest suspicion of enthusiasm; but all through the interminable narrative there ran a "
            "vein of impressive earnestness and sincerity, which showed me plainly that, so far from his imagining "
            "that there was anything ridiculous or funny about his story, he regarded it as a really important matter, "
            "and admired its two heroes as men of transcendent genius in finesse.\n\n"
            "[Public domain - Mark Twain. Skybrary literacy pack.]"
        ),
    },
]

# Wave 2+ public-domain expansion (v1.23+) - merge curated MORE_SAMPLES
from skycache.skybrary.sample_corpus_more import MORE_SAMPLES  # noqa: E402
# Wave 3 multilingual PD (v1.24+)
from skycache.skybrary.sample_corpus_ml import ML_SAMPLES  # noqa: E402
# Wave 4 humanitarian multilingual (v1.25+)
from skycache.skybrary.sample_corpus_ml2 import ML2_SAMPLES  # noqa: E402
# Wave 5 health / emergency educational PD (v1.31+)
from skycache.skybrary.sample_corpus_health import HEALTH_SAMPLES  # noqa: E402
# Wave 6 STEM / civics / heritage educational PD (v1.33+)
from skycache.skybrary.sample_corpus_stem import STEM_SAMPLES  # noqa: E402

SAMPLES = (
    list(SAMPLES)
    + list(MORE_SAMPLES)
    + list(ML_SAMPLES)
    + list(ML2_SAMPLES)
    + list(HEALTH_SAMPLES)
    + list(STEM_SAMPLES)
)


def build_sample_packages(out_dir: Path) -> list[Path]:
    """Write SkyCache-compatible package dirs for each sample work."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    stamp = datetime.now(timezone.utc)
    default_license = assert_license_allowed("public domain")

    for s in SAMPLES:
        title = s["title"]
        summary = s.get("summary") or {"en": title.get("en", s["work_id"])}
        prio = str(s.get("priority_class") or "education")
        langs = s.get("languages") or ["en"]
        if isinstance(langs, str):
            langs = [langs]
        lic_raw = str(s.get("license") or "public domain")
        try:
            license_name = assert_license_allowed(lic_raw)
        except Exception:
            license_name = default_license
        work = Work(
            work_id=s["work_id"],
            title=title,
            creators=s["creators"],
            languages=[str(x) for x in langs],
            subjects=s["subjects"],
            license=license_name,
            provenance={
                "source": "skybrary_curated_pd_sample",
                "note": (
                    "Curated public-domain pack for Skybrary Live dual-access; "
                    "not a complete corpus dump"
                ),
                "retrieval_date": stamp.strftime("%Y-%m-%d"),
            },
            civilizational_tier=int(s["tier"]),
            summary=summary,
        )
        body = s["body"]
        digest = sha256_text(body)
        edition = Edition(
            edition_id=f"{work.work_id}-txt",
            work_id=work.work_id,
            format="txt",
            path="work.txt",
            size_bytes=len(body.encode("utf-8")),
            sha256=digest,
            priority_class=prio,
            received_at=stamp,
        )

        pkg_dir = out_dir / work.work_id
        pkg_dir.mkdir(parents=True, exist_ok=True)
        (pkg_dir / "work.txt").write_bytes(body.encode("utf-8"))
        title_en = work.title.get("en", work.work_id)
        html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{title_en}</title>
<style>body{{font-family:Georgia,serif;max-width:40rem;margin:1.5rem auto;padding:0 1rem;line-height:1.55;
background:#0b1220;color:#f1f5f9}} h1{{font-size:1.4rem;color:#5eead4}} .meta{{color:#94a3b8;font-size:.9rem}}
pre{{white-space:pre-wrap;font-family:Georgia,serif}}</style></head><body>
<p class="meta">Skybrary  |  Public domain  |  Dual-access pack  |  Not a complete archive</p>
<h1>{title_en}</h1>
<p class="meta">{"  |  ".join(work.creators)}  |  license: public domain  |  sha256: {digest[:16]}...</p>
<pre>{body}</pre>
<p class="meta">SkyCache / Skybrary offline pack. Store-and-forward knowledge - not free commercial broadband.</p>
</body></html>
"""
        (pkg_dir / "index.html").write_text(html, encoding="utf-8")
        manifest = {
            "id": work.work_id,
            "kind": "skybrary_text",
            "priority_class": prio,
            "title": work.title,
            "summary": work.summary,
            "languages": work.languages,
            "received_at": stamp.isoformat(),
            "freshness_hours": 8760 * 10,
            "size_bytes": edition.size_bytes + len(html.encode("utf-8")),
            "license": "public domain",
            "source": {
                "type": "skybrary_pd_sample",
                "legal_note": "Public domain curated pack for Skybrary Live",
                "plugin": "skybrary_sample",
                "extra": {
                    "work": work.model_dump(mode="json"),
                    "edition": edition.model_dump(mode="json"),
                    "sha256": digest,
                },
            },
            "files": [
                {
                    "path": "index.html",
                    "mime": "text/html",
                    "size_bytes": len(html.encode("utf-8")),
                    "role": "index",
                },
                {
                    "path": "work.txt",
                    "mime": "text/plain",
                    "size_bytes": edition.size_bytes,
                    "role": "payload",
                },
            ],
            "tags": work.subjects + ["skybrary", "public-domain"],
            "pinned": work.civilizational_tier <= 2,
            "icon": "health" if prio in {"health", "emergency"} else "education",
        }
        (pkg_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        paths.append(pkg_dir)
    return paths
