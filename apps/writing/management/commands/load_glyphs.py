import io
from pathlib import Path

import cairosvg
import cv2
import numpy as np
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image

from apps.writing.models import Glyph
from apps.writing.services import svg_service


class Command(BaseCommand):
    help = "Load Sitelen Pona glyphs from static SVG files"

    def handle(self, *args, **kwargs):
        """Handle the command execution."""
        self.stdout.write(
            self.style.NOTICE("Loading Sitelen Pona glyphs from static files...")
        )

        self._cleanup_legacy_directories()
        self._ensure_media_directories()

        # Source SVG directory in static files
        svg_source_dir = self._get_svg_source_dir()
        if not svg_source_dir:
            return

        # Find all SVG files
        svg_files = self._find_svg_files(svg_source_dir)
        if not svg_files:
            return

        # Process the SVG files
        self._process_svg_files(svg_files)

    def _cleanup_legacy_directories(self):
        """Clean up old incorrect model directory if it exists."""
        root_ml_models = Path(settings.BASE_DIR) / "ml_models"
        if root_ml_models.exists() and root_ml_models.is_dir():
            import shutil

            self.stdout.write(
                self.style.WARNING(
                    "Removing legacy ml_models directory at project root..."
                )
            )
            try:
                shutil.rmtree(root_ml_models)
                self.stdout.write(
                    self.style.SUCCESS(f"Removed legacy directory: {root_ml_models}")
                )
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error removing directory: {e}"))

    def _ensure_media_directories(self):
        """Ensure necessary media directories exist."""
        # Check media directories
        media_dir = Path(settings.MEDIA_ROOT)
        if not media_dir.exists():
            media_dir.mkdir(parents=True)

        glyphs_dir = media_dir / "glyphs"
        if not glyphs_dir.exists():
            glyphs_dir.mkdir(parents=True)

        reference_dir = glyphs_dir / "reference"
        if not reference_dir.exists():
            reference_dir.mkdir(parents=True)

    def _get_svg_source_dir(self):
        """Get the source directory for SVG files."""
        svg_source_dir = Path(
            settings.ML_MODELS_STORAGE.get(
                "STATIC_GLYPHS_DIR",
                Path(settings.BASE_DIR) / "static" / "images" / "glyphs",
            )
        )

        # Check if source directory exists
        if not svg_source_dir.exists():
            self.stderr.write(
                self.style.ERROR(
                    f"Source SVG directory '{svg_source_dir}' does not exist"
                )
            )
            return None

        return svg_source_dir

    def _find_svg_files(self, svg_source_dir):
        """Find all SVG files in the source directory."""
        svg_files = list(svg_source_dir.glob("*.svg"))
        if not svg_files:
            self.stderr.write(
                self.style.WARNING(f"No SVG files found in '{svg_source_dir}'")
            )
            return None

        self.stdout.write(self.style.NOTICE(f"Found {len(svg_files)} SVG files"))
        return svg_files

    def _get_glyph_metadata(self):
        """Define metadata for glyphs."""
        # Define glyph metadata for all core Toki Pona words
        glyph_metadata = {
            "a": {
                "meaning": "ah, ha, emphasis, emotion word",
                "difficulty": "beginner",
                "category": "grammar",
                "example_sentence": "pona a!",
                "description": "The glyph for 'a' resembles an exclamation mark, conveying emphasis or emotion.",
            },
            "akesi": {
                "meaning": "reptile, amphibian, non-cute animal",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "akesi li tawa lon telo",
                "description": "The glyph for 'akesi' depicts a small reptilian creature.",
            },
            "ala": {
                "meaning": "no, not, zero, none",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi wile ala tawa",
                "description": "The glyph for 'ala' shows emptiness or nullity.",
            },
            "alasa": {
                "meaning": "hunt, forage, gather, search",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi alasa e kili",
                "description": "The glyph for 'alasa' shows a figure hunting or searching.",
            },
            "ale": {
                "meaning": "all, everything, universe, 100",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "ale li pona",
                "description": "The glyph for 'ale' represents wholeness or completeness.",
            },
            "anpa": {
                "meaning": "bottom, down, humble, lowly",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi anpa e mi",
                "description": "The glyph for 'anpa' points downward, showing lowness.",
            },
            "ante": {
                "meaning": "different, changed, altered",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "ni li ante",
                "description": "The glyph for 'ante' shows transformation or change.",
            },
            "anu": {
                "meaning": "or, choice question marker",
                "difficulty": "beginner",
                "category": "grammar",
                "example_sentence": "sina wile e telo anu moku?",
                "description": "The glyph for 'anu' shows a branching path or choice.",
            },
            "awen": {
                "meaning": "stay, wait, remain, protect",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi awen lon ni",
                "description": "The glyph for 'awen' represents stability and permanence.",
            },
            "e": {
                "meaning": "object marker",
                "difficulty": "beginner",
                "category": "grammar",
                "example_sentence": "mi moku e kili",
                "description": "The glyph for 'e' is a simple mark that indicates an object.",
            },
            "en": {
                "meaning": "and (combines subjects)",
                "difficulty": "beginner",
                "category": "grammar",
                "example_sentence": "mi en sina li pona",
                "description": "The glyph for 'en' shows a connection between things.",
            },
            "esun": {
                "meaning": "market, shop, trade, exchange",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi tawa esun",
                "description": "The glyph for 'esun' resembles a marketplace or trading post.",
            },
            "ijo": {
                "meaning": "thing, object, matter, stuff",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "ijo ni li suli",
                "description": "The glyph for 'ijo' represents a general object or thing.",
            },
            "ike": {
                "meaning": "bad, negative, wrong, evil",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "ni li ike",
                "description": "The glyph for 'ike' represents negativity or badness.",
            },
            "ilo": {
                "meaning": "tool, machine, device",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi kepeken ilo",
                "description": "The glyph for 'ilo' represents a tool or implement.",
            },
            "insa": {
                "meaning": "inside, contents, center",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi tawa insa tomo",
                "description": "The glyph for 'insa' shows an enclosed inner space.",
            },
            "jaki": {
                "meaning": "dirty, disgusting, toxic",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "ni li jaki",
                "description": "The glyph for 'jaki' represents contamination or filth.",
            },
            "jan": {
                "meaning": "person, human, somebody",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "jan li pona",
                "description": "The glyph for 'jan' resembles a simple figure of a person.",
            },
            "jelo": {
                "meaning": "yellow, yellowish",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "kasi li jelo",
                "description": "The glyph for 'jelo' represents the color yellow.",
            },
            "jo": {
                "meaning": "have, carry, contain, hold",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi jo e ilo",
                "description": "The glyph for 'jo' shows possession or holding.",
            },
            "kala": {
                "meaning": "fish, marine animal",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "kala li lon telo",
                "description": "The glyph for 'kala' resembles a fish.",
            },
            "kalama": {
                "meaning": "sound, noise, voice",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi kute e kalama",
                "description": "The glyph for 'kalama' represents sound waves.",
            },
            "kama": {
                "meaning": "come, happen, appear, future",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi kama tawa sina",
                "description": "The glyph for 'kama' shows movement toward a destination.",
            },
            "kasi": {
                "meaning": "plant, vegetation, herb",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "kasi li lon ma",
                "description": "The glyph for 'kasi' depicts a growing plant.",
            },
            "ken": {
                "meaning": "can, able to, possible",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi ken pali e ni",
                "description": "The glyph for 'ken' represents capability or possibility.",
            },
            "kepeken": {
                "meaning": "use, with, using",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi pali kepeken ilo",
                "description": "The glyph for 'kepeken' shows a hand using a tool.",
            },
            "kili": {
                "meaning": "fruit, vegetable, mushroom",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi moku e kili",
                "description": "The glyph for 'kili' depicts a fruit or vegetable.",
            },
            "kiwen": {
                "meaning": "hard, solid, stone, metal",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi lon kiwen",
                "description": "The glyph for 'kiwen' represents hardness or solidity.",
            },
            "ko": {
                "meaning": "powder, clay, paste, semi-solid",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi kepeken ko",
                "description": "The glyph for 'ko' represents a semi-solid or paste-like substance.",
            },
            "kon": {
                "meaning": "air, spirit, essence",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi pilin e kon",
                "description": "The glyph for 'kon' shows air or wind movement.",
            },
            "kule": {
                "meaning": "color, paint",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "ni li kule pona",
                "description": "The glyph for 'kule' represents various colors.",
            },
            "kulupu": {
                "meaning": "group, community, society",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi lon kulupu",
                "description": "The glyph for 'kulupu' shows several figures together.",
            },
            "kute": {
                "meaning": "hear, listen, obey",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi kute e sina",
                "description": "The glyph for 'kute' depicts an ear or listening.",
            },
            "la": {
                "meaning": "context marker (if, when)",
                "difficulty": "beginner",
                "category": "grammar",
                "example_sentence": "tenpo pimeja la mi lape",
                "description": "The glyph for 'la' represents a contextual transition.",
            },
            "lape": {
                "meaning": "sleep, rest",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi wile lape",
                "description": "The glyph for 'lape' shows a sleeping figure.",
            },
            "laso": {
                "meaning": "blue, green",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "sewi li laso",
                "description": "The glyph for 'laso' represents blue-green colors.",
            },
            "lawa": {
                "meaning": "head, control, rule, main",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi lawa e kulupu",
                "description": "The glyph for 'lawa' depicts a head or leadership.",
            },
            "len": {
                "meaning": "clothing, cloth, fabric",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi jo e len",
                "description": "The glyph for 'len' represents clothing or fabric.",
            },
            "lete": {
                "meaning": "cold, cool, uncooked",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "telo ni li lete",
                "description": "The glyph for 'lete' represents coldness or cooling.",
            },
            "li": {
                "meaning": "predicate marker",
                "difficulty": "beginner",
                "category": "grammar",
                "example_sentence": "sina li pona",
                "description": "The glyph for 'li' is a simple mark that separates subject and predicate.",
            },
            "lili": {
                "meaning": "small, little, young",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "jan lili li lape",
                "description": "The glyph for 'lili' depicts smallness or diminution.",
            },
            "linja": {
                "meaning": "line, hair, string, rope",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi jo e linja",
                "description": "The glyph for 'linja' shows a line or string-like form.",
            },
            "lipu": {
                "meaning": "paper, document, book",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi lukin e lipu",
                "description": "The glyph for 'lipu' represents a flat surface like paper.",
            },
            "loje": {
                "meaning": "red",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "kili ni li loje",
                "description": "The glyph for 'loje' represents the color red.",
            },
            "lon": {
                "meaning": "at, in, on, exists, true",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi lon tomo",
                "description": "The glyph for 'lon' represents presence or existence.",
            },
            "luka": {
                "meaning": "hand, arm, tactile sense",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi kepeken luka mi",
                "description": "The glyph for 'luka' depicts a hand with fingers.",
            },
            "lukin": {
                "meaning": "see, look, watch, eye",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi lukin e sina",
                "description": "The glyph for 'lukin' resembles an eye.",
            },
            "lupa": {
                "meaning": "hole, door, window, orifice",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi tawa lon lupa",
                "description": "The glyph for 'lupa' represents an opening or hole.",
            },
            "ma": {
                "meaning": "land, country, earth, outdoor",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi lon ma",
                "description": "The glyph for 'ma' represents land or territory.",
            },
            "mama": {
                "meaning": "parent, caregiver, creator",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mama mi li pona",
                "description": "The glyph for 'mama' depicts a parental figure.",
            },
            "mani": {
                "meaning": "money, wealth, large domesticated animal",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi jo e mani",
                "description": "The glyph for 'mani' represents currency or value.",
            },
            "meli": {
                "meaning": "woman, female, feminine",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "meli ni li pona",
                "description": "The glyph for 'meli' depicts a female figure.",
            },
            "mi": {
                "meaning": "I, me, we, us",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi moku",
                "description": "The glyph for 'mi' points to oneself.",
            },
            "mije": {
                "meaning": "man, male, masculine",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mije li pali",
                "description": "The glyph for 'mije' depicts a male figure.",
            },
            "moku": {
                "meaning": "food, eat, drink, consume",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi moku e kili",
                "description": "The glyph for 'moku' represents eating or food.",
            },
            "moli": {
                "meaning": "death, dying, kill",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "kasi li moli",
                "description": "The glyph for 'moli' represents death or ending.",
            },
            "monsi": {
                "meaning": "back, behind, rear",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi lon monsi sina",
                "description": "The glyph for 'monsi' indicates the back or behind position.",
            },
            "mu": {
                "meaning": "animal sound, communication",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "soweli li mu",
                "description": "The glyph for 'mu' represents animal sounds or non-human communication.",
            },
            "mun": {
                "meaning": "moon, star, night sky object",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mun li lon sewi",
                "description": "The glyph for 'mun' depicts the moon.",
            },
            "musi": {
                "meaning": "fun, play, game, art",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi musi",
                "description": "The glyph for 'musi' represents playfulness or entertainment.",
            },
            "mute": {
                "meaning": "many, more, quantity",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "jan mute li kama",
                "description": "The glyph for 'mute' represents plurality or abundance.",
            },
            "nanpa": {
                "meaning": "number, count, ordinal",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "ni li nanpa wan",
                "description": "The glyph for 'nanpa' represents counting or enumeration.",
            },
            "nasa": {
                "meaning": "strange, silly, drunk",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "jan ni li nasa",
                "description": "The glyph for 'nasa' represents strangeness or peculiarity.",
            },
            "nasin": {
                "meaning": "way, path, doctrine, method",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi tawa lon nasin",
                "description": "The glyph for 'nasin' depicts a path or way.",
            },
            "nena": {
                "meaning": "hill, bump, nose, mountain",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi lon nena",
                "description": "The glyph for 'nena' represents an elevated form or protrusion.",
            },
            "ni": {
                "meaning": "this, that",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "ni li pona",
                "description": "The glyph for 'ni' indicates something specific.",
            },
            "nimi": {
                "meaning": "word, name",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "nimi mi li jan",
                "description": "The glyph for 'nimi' represents words or language units.",
            },
            "noka": {
                "meaning": "foot, leg, bottom part",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi tawa kepeken noka",
                "description": "The glyph for 'noka' depicts a foot or leg.",
            },
            "o": {
                "meaning": "hey! command, request",
                "difficulty": "beginner",
                "category": "grammar",
                "example_sentence": "o kama!",
                "description": "The glyph for 'o' represents a call to attention or command.",
            },
            "olin": {
                "meaning": "love, compassion, affection",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi olin e sina",
                "description": "The glyph for 'olin' represents love or affection.",
            },
            "ona": {
                "meaning": "he, she, it, they",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "ona li pona",
                "description": "The glyph for 'ona' represents a third person.",
            },
            "open": {
                "meaning": "open, start, begin",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi open e pali",
                "description": "The glyph for 'open' represents beginning or initiation.",
            },
            "pakala": {
                "meaning": "broken, damaged, mistake",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "ilo li pakala",
                "description": "The glyph for 'pakala' represents damage or breakage.",
            },
            "pali": {
                "meaning": "do, make, work, create",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi pali e tomo",
                "description": "The glyph for 'pali' depicts activity or work.",
            },
            "palisa": {
                "meaning": "rod, stick, long hard thing",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi kepeken palisa",
                "description": "The glyph for 'palisa' represents an elongated object.",
            },
            "pan": {
                "meaning": "bread, grain, cereal",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi moku e pan",
                "description": "The glyph for 'pan' depicts bread or grain.",
            },
            "pana": {
                "meaning": "give, send, emit, provide",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi pana e mani",
                "description": "The glyph for 'pana' represents giving or sending.",
            },
            "pi": {
                "meaning": "of, belonging to (regroups modifiers)",
                "difficulty": "intermediate",
                "category": "grammar",
                "example_sentence": "jan pi ma tomo",
                "description": "The glyph for 'pi' indicates possession or association.",
            },
            "pilin": {
                "meaning": "heart, feeling, emotion",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi pilin pona",
                "description": "The glyph for 'pilin' depicts a heart or emotional center.",
            },
            "pimeja": {
                "meaning": "black, dark",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "tomo li pimeja",
                "description": "The glyph for 'pimeja' represents darkness or blackness.",
            },
            "pini": {
                "meaning": "end, finish, close",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi pini e ni",
                "description": "The glyph for 'pini' represents conclusion or ending.",
            },
            "pipi": {
                "meaning": "bug, insect, ant",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "pipi li lon ma",
                "description": "The glyph for 'pipi' depicts a small insect.",
            },
            "poka": {
                "meaning": "side, hip, next to",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi lon poka sina",
                "description": "The glyph for 'poka' represents adjacency or being beside.",
            },
            "poki": {
                "meaning": "container, box, bowl, cup",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi jo e poki",
                "description": "The glyph for 'poki' depicts a container or vessel.",
            },
            "pona": {
                "meaning": "good, simple, positive",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "sina pona",
                "description": "The glyph for 'pona' has a simple design representing goodness.",
            },
            "pu": {
                "meaning": "interacting with the official Toki Pona book",
                "difficulty": "advanced",
                "category": "compound",
                "example_sentence": "mi pu",
                "description": "The glyph for 'pu' references the official Toki Pona book.",
            },
            "sama": {
                "meaning": "same, similar, sibling, peer",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "ni li sama ni",
                "description": "The glyph for 'sama' represents similarity or sameness.",
            },
            "seli": {
                "meaning": "fire, heat, warm",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi seli e moku",
                "description": "The glyph for 'seli' depicts flames or heat.",
            },
            "selo": {
                "meaning": "skin, bark, shell, boundary",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "selo mi li loje",
                "description": "The glyph for 'selo' represents an outer covering.",
            },
            "seme": {
                "meaning": "what? which?",
                "difficulty": "beginner",
                "category": "grammar",
                "example_sentence": "sina wile e seme?",
                "description": "The glyph for 'seme' represents questioning or inquiry.",
            },
            "sewi": {
                "meaning": "high, above, divine, sacred",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "waso li lon sewi",
                "description": "The glyph for 'sewi' points upward or represents elevation.",
            },
            "sijelo": {
                "meaning": "body, physical state",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "sijelo mi li pona",
                "description": "The glyph for 'sijelo' represents a body or physical form.",
            },
            "sike": {
                "meaning": "circle, ball, cycle, round",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi jo e sike",
                "description": "The glyph for 'sike' depicts a circle or circular motion.",
            },
            "sin": {
                "meaning": "new, fresh, additional",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "ni li sin",
                "description": "The glyph for 'sin' represents newness or novelty.",
            },
            "sina": {
                "meaning": "you",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "sina suli",
                "description": "The glyph for 'sina' points outward to someone else.",
            },
            "sinpin": {
                "meaning": "face, front, wall",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi lukin e sinpin sina",
                "description": "The glyph for 'sinpin' represents a front surface or face.",
            },
            "sitelen": {
                "meaning": "image, picture, symbol, write",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi sitelen e ni",
                "description": "The glyph for 'sitelen' depicts drawing or imagery.",
            },
            "sona": {
                "meaning": "know, knowledge, wisdom",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi sona e ni",
                "description": "The glyph for 'sona' represents knowledge or understanding.",
            },
            "soweli": {
                "meaning": "animal, land mammal",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "soweli li lili",
                "description": "The glyph for 'soweli' depicts a four-legged animal.",
            },
            "suli": {
                "meaning": "big, great, important",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "ni li suli",
                "description": "The glyph for 'suli' represents largeness or importance.",
            },
            "suno": {
                "meaning": "sun, light, shine",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "suno li seli",
                "description": "The glyph for 'suno' depicts the sun with radiating rays.",
            },
            "supa": {
                "meaning": "horizontal surface, furniture",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi lon supa",
                "description": "The glyph for 'supa' represents a flat surface or platform.",
            },
            "suwi": {
                "meaning": "sweet, cute, adorable",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "moku ni li suwi",
                "description": "The glyph for 'suwi' represents sweetness or cuteness.",
            },
            "tan": {
                "meaning": "from, by, because of",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "mi kama tan ma mi",
                "description": "The glyph for 'tan' represents origin or causation.",
            },
            "taso": {
                "meaning": "but, however, only",
                "difficulty": "intermediate",
                "category": "grammar",
                "example_sentence": "mi wile tawa taso mi ken ala",
                "description": "The glyph for 'taso' represents limitation or exception.",
            },
            "tawa": {
                "meaning": "go, move, toward",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi tawa ma sina",
                "description": "The glyph for 'tawa' represents movement or motion.",
            },
            "telo": {
                "meaning": "water, liquid, fluid",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi moku e telo",
                "description": "The glyph for 'telo' represents water or fluidity.",
            },
            "tenpo": {
                "meaning": "time, duration, moment",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "tenpo ni la mi moku",
                "description": "The glyph for 'tenpo' represents the passing of time.",
            },
            "toki": {
                "meaning": "language, communicate, talk, speech",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "toki pona li pona",
                "description": "The glyph for 'toki' resembles a mouth talking.",
            },
            "tomo": {
                "meaning": "house, building, structure",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi lon tomo mi",
                "description": "The glyph for 'tomo' depicts a simple house or building.",
            },
            "tu": {
                "meaning": "two, divide, split",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi jo e kili tu",
                "description": "The glyph for 'tu' represents duality or division.",
            },
            "unpa": {
                "meaning": "sexual, intimate",
                "difficulty": "advanced",
                "category": "basic",
                "example_sentence": "jan tu li unpa",
                "description": "The glyph for 'unpa' represents intimacy between beings.",
            },
            "uta": {
                "meaning": "mouth, lips, oral",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi moku kepeken uta",
                "description": "The glyph for 'uta' depicts a mouth or lips.",
            },
            "utala": {
                "meaning": "fight, conflict, compete",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "jan tu li utala",
                "description": "The glyph for 'utala' represents conflict or struggle.",
            },
            "walo": {
                "meaning": "white, light-colored",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "len mi li walo",
                "description": "The glyph for 'walo' represents whiteness or light colors.",
            },
            "wan": {
                "meaning": "one, unite, unique",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi wile wan",
                "description": "The glyph for 'wan' represents singularity or unity.",
            },
            "waso": {
                "meaning": "bird, flying creature",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "waso li lon sewi",
                "description": "The glyph for 'waso' depicts a bird with wings.",
            },
            "wawa": {
                "meaning": "strong, powerful, energetic",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi wawa",
                "description": "The glyph for 'wawa' represents strength or power.",
            },
            "weka": {
                "meaning": "away, absent, remove",
                "difficulty": "intermediate",
                "category": "basic",
                "example_sentence": "ona li weka",
                "description": "The glyph for 'weka' represents distance or absence.",
            },
            "wile": {
                "meaning": "want, need, desire, must",
                "difficulty": "beginner",
                "category": "basic",
                "example_sentence": "mi wile moku",
                "description": "The glyph for 'wile' represents desire or need.",
            },
        }

        # Default metadata for unknown glyphs
        default_metadata = {
            "meaning": "Toki Pona word",
            "difficulty": "intermediate",
            "category": "basic",
            "example_sentence": "",
            "description": "Sitelen Pona glyph",
        }

        return glyph_metadata, default_metadata

    def _process_svg_files(self, svg_files):
        """Process each SVG file."""
        glyph_metadata, default_metadata = self._get_glyph_metadata()

        # Import and process each SVG file
        processed_count = 0
        for svg_file in svg_files:
            glyph_name = svg_file.stem  # Get filename without extension

            # Check if glyph already exists
            existing_glyph = Glyph.objects.filter(name=glyph_name).first()
            if existing_glyph:
                self.stdout.write(
                    self.style.WARNING(
                        f"Glyph '{glyph_name}' already exists, updating..."
                    )
                )

            try:
                processed = self._process_single_svg(
                    svg_file,
                    glyph_name,
                    glyph_metadata,
                    default_metadata,
                    existing_glyph,
                )
                if processed:
                    processed_count += 1

            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f"Error processing {glyph_name}: {e}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully processed {processed_count} out of {len(svg_files)} glyphs"
            )
        )

    def _process_single_svg(
        self,
        svg_file,
        glyph_name,
        glyph_metadata,
        default_metadata,
        existing_glyph=None,
    ):
        """Process a single SVG file."""
        # Read the SVG content
        with open(svg_file, "r", encoding="utf-8") as f:
            svg_content = f.read()

        # Upload SVG to service (makes it available via API/templates)
        svg_service.upload_svg(glyph_name, svg_content)

        # Convert SVG to PNG for ML model
        png_data = cairosvg.svg2png(
            bytestring=svg_content.encode("utf-8"),
            output_width=100,
            output_height=100,
            background_color="white",
        )

        # Convert to numpy array for processing
        image = Image.open(io.BytesIO(png_data))
        image_array = np.array(image)

        # Convert to grayscale if needed
        if len(image_array.shape) == 3:
            image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)

        # Threshold to create binary image
        _, binary = cv2.threshold(image_array, 127, 255, cv2.THRESH_BINARY)

        # Save processed image to bytes
        processed_img = cv2.imencode(".png", binary)[1].tobytes()

        # Also create a template image for character recognition
        from apps.writing.services.templates import template_service

        template_service.upload_template(glyph_name, processed_img)

        # Get glyph metadata (or use defaults)
        metadata = glyph_metadata.get(glyph_name, default_metadata)

        # Update or create the glyph record
        glyph = existing_glyph or Glyph(name=glyph_name)
        glyph.meaning = metadata["meaning"]
        glyph.difficulty = metadata["difficulty"]
        glyph.category = metadata["category"]
        glyph.example_sentence = metadata["example_sentence"]
        glyph.description = metadata["description"]

        # Save to create or update the model instance
        glyph.save()

        # Add both the processed PNG and original SVG to the model
        # For ML recognition
        glyph.image.save(f"{glyph_name}.png", ContentFile(processed_img), save=False)

        # For reference display
        glyph.reference_image.save(
            f"{glyph_name}.svg",
            ContentFile(svg_content.encode("utf-8")),
            save=True,
        )

        self.stdout.write(self.style.SUCCESS(f"Processed glyph: {glyph_name}"))
        return True
