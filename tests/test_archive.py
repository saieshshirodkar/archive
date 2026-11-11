from __future__ import annotations

import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import add as add_mod  # noqa: E402
import archive as A  # noqa: E402
import rate as rate_mod  # noqa: E402
import reorder as reorder_mod  # noqa: E402

MAGICK = shutil.which("magick") or shutil.which("convert")

BOOKS = [
    {
        "id": 1,
        "title": "Alpha",
        "author": "A One",
        "rating_text": "8/10",
        "cover_url": "assets/covers/books/alpha.webp",
        "year": 2020,
        "width": 400,
        "height": 600,
    },
    {
        "id": 2,
        "title": "Beta",
        "author": "B Two",
        "rating_text": "9/10",
        "cover_url": "assets/covers/books/beta.webp",
        "year": 2021,
        "width": 400,
        "height": 600,
    },
    {
        "id": 3,
        "title": "Gamma",
        "author": "C Three",
        "rating_text": "7/10",
        "cover_url": "assets/covers/books/gamma.webp",
        "year": 2022,
        "width": 400,
        "height": 600,
    },
]

MOVIES = [
    {
        "id": 1,
        "title": "Movie One",
        "year": 2019,
        "date_watched": "01-01-2019",
        "rating_text": "8/10",
        "cover_url": "assets/covers/movies/one.webp",
        "width": 400,
        "height": 600,
    },
    {
        "id": 2,
        "title": "Movie Two",
        "year": 2020,
        "date_watched": "02-02-2020",
        "rating_text": "9/10",
        "cover_url": "assets/covers/movies/two.webp",
        "width": 400,
        "height": 600,
    },
]

SHOWS = [
    {
        "id": 1,
        "title": "Show One",
        "rating_text": "8/10",
        "cover_url": "assets/covers/shows/one.webp",
        "year": 2019,
        "width": 400,
        "height": 600,
    },
    {
        "id": 2,
        "title": "Show Two",
        "rating_text": "9/10",
        "cover_url": "assets/covers/shows/two.webp",
        "year": 2020,
        "width": 400,
        "height": 600,
    },
    {
        "id": 3,
        "title": "Show Three",
        "rating_text": "7/10",
        "cover_url": "assets/covers/shows/three.webp",
        "year": 2021,
        "width": 400,
        "height": 600,
    },
]

ANIMANGA = [
    {
        "id": 1,
        "title": "Manga One",
        "author": "M One",
        "rating_text": "8/10",
        "cover_url": "assets/covers/anime/one.webp",
        "year": 2019,
        "width": 400,
        "height": 600,
    }
]


_COVER_CACHE: dict[str, bytes] = {}


def cover_bytes() -> bytes:
    if "stub" not in _COVER_CACHE:
        if MAGICK:
            with tempfile.TemporaryDirectory() as td:
                probe = Path(td) / "probe.webp"
                subprocess.run(
                    [
                        MAGICK,
                        "-size",
                        "400x600",
                        "xc:black",
                        "-quality",
                        "80",
                        str(probe),
                    ],
                    check=True,
                    capture_output=True,
                )
                _COVER_CACHE["stub"] = probe.read_bytes()
        else:
            _COVER_CACHE["stub"] = b"stub"
    return _COVER_CACHE["stub"]


def make_cover(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(cover_bytes())


def build_root(root: Path) -> None:
    for folder in ("books", "anime", "movies", "shows"):
        (root / "assets" / "covers" / folder).mkdir(parents=True, exist_ok=True)
    (root / "data").mkdir(parents=True, exist_ok=True)
    payload = {
        "books": BOOKS,
        "animanga": ANIMANGA,
        "movies": MOVIES,
        "shows": SHOWS,
    }
    for cat, entries in payload.items():
        (root / "data" / f"{cat}.json").write_text(
            json.dumps(entries, indent=2) + "\n", encoding="utf-8"
        )
        for entry in entries:
            make_cover(root / entry["cover_url"])


class Sandbox:
    def __init__(self, root: Path):
        self.root = root

    def __enter__(self) -> Sandbox:
        self._saved = (A.ROOT, A.DATA_DIR, A.COVERS_DIR)
        A.ROOT = self.root
        A.DATA_DIR = self.root / "data"
        A.COVERS_DIR = self.root / "assets" / "covers"
        return self

    def __exit__(self, *exc: object) -> None:
        A.ROOT, A.DATA_DIR, A.COVERS_DIR = self._saved


class SandboxCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        build_root(self.root)
        self.sandbox = Sandbox(self.root)
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)
        self.addCleanup(self._tmp.cleanup)

    def titles(self, cat: str) -> list[str]:
        return [e["title"] for e in A.load(cat)]

    def ids(self, cat: str) -> list[int]:
        return [e["id"] for e in A.load(cat)]

    def read(self, cat: str) -> str:
        return (self.root / "data" / f"{cat}.json").read_text(encoding="utf-8")


class TestMove(unittest.TestCase):
    def test_moving_down_lands_on_the_target_index(self) -> None:
        for index, to in ((0, 2), (0, 3), (1, 3), (2, 4)):
            entries = list("ABCDE")
            moved = entries[index]
            A.move(entries, index, to)
            self.assertEqual(entries[to], moved, f"move({index}, {to})")
            self.assertEqual(len(entries), 5)

    def test_moving_up_lands_on_the_target_index(self) -> None:
        for index, to in ((4, 1), (4, 0), (3, 1), (2, 0)):
            entries = list("ABCDE")
            moved = entries[index]
            A.move(entries, index, to)
            self.assertEqual(entries[to], moved, f"move({index}, {to})")

    def test_clamps_to_bounds(self) -> None:
        entries = list("ABCDE")
        A.move(entries, 0, 99)
        self.assertEqual(entries, list("BCDEA"))
        entries = list("ABCDE")
        A.move(entries, 4, -5)
        self.assertEqual(entries, list("EABCD"))

    def test_same_index_is_a_noop(self) -> None:
        entries = list("ABCDE")
        A.move(entries, 2, 2)
        self.assertEqual(entries, list("ABCDE"))

    def test_out_of_range_index_raises(self) -> None:
        with self.assertRaises(IndexError):
            A.move(list("ABCDE"), 5, 0)


class TestAnchorTarget(unittest.TestCase):
    def test_before(self) -> None:
        cases = {
            (0, 3): 2,
            (4, 1): 1,
            (0, 1): 0,
            (1, 4): 3,
        }
        for (index, found), expected in cases.items():
            self.assertEqual(
                reorder_mod.anchor_target(index, found, "before"), expected
            )

    def test_after(self) -> None:
        cases = {
            (0, 2): 2,
            (4, 2): 3,
            (0, 0): 1,
            (3, 1): 2,
        }
        for (index, found), expected in cases.items():
            self.assertEqual(reorder_mod.anchor_target(index, found, "after"), expected)


class TestNormalise(unittest.TestCase):
    def test_renumbers_and_orders_keys(self) -> None:
        entries = [
            {
                "title": "B",
                "rating_text": "8/10",
                "cover_url": "x.webp",
                "year": 1,
                "width": 400,
                "height": 600,
            },
            {
                "title": "A",
                "rating_text": "8/10",
                "cover_url": "y.webp",
                "year": 2,
                "width": 400,
                "height": 600,
            },
        ]
        out = A.normalise("shows", entries)
        self.assertEqual([e["id"] for e in out], [1, 2])
        self.assertEqual(list(out[0]), A.CATEGORIES["shows"]["keys"])

    def test_missing_key_raises(self) -> None:
        with self.assertRaises(KeyError):
            A.normalise("shows", [{"title": "A"}])


class TestRating(unittest.TestCase):
    def test_accepts(self) -> None:
        self.assertEqual(A.normalise_rating("8"), "8/10")
        self.assertEqual(A.normalise_rating("8.5"), "8.5/10")
        self.assertEqual(A.normalise_rating("10"), "10/10")
        self.assertEqual(A.normalise_rating("8/10"), "8/10")

    def test_rejects(self) -> None:
        for bad in ("7/5", "11", "-1", "", "abc", "8/100"):
            with self.assertRaises(ValueError, msg=bad):
                A.normalise_rating(bad)


class TestSlugify(unittest.TestCase):
    def test_cases(self) -> None:
        cases = {
            "Dune": "dune",
            "The F**k-It List": "the-fk-it-list",
            "Takopi's": "takopis",
            "Bastard!!": "bastard",
            "Sword Art Online: Alicization": "sword-art-online-alicization",
        }
        for title, expected in cases.items():
            self.assertEqual(A.slugify(title), expected)


class TestParseWatched(unittest.TestCase):
    def test_parses(self) -> None:
        self.assertEqual(A.parse_watched("01-02-2020"), [2020, 2, 1])

    def test_rejects_impossible_dates(self) -> None:
        for bad in ("99-99-2026", "2026-01-01", "", "not-a-date"):
            with self.assertRaises(ValueError, msg=bad):
                A.parse_watched(bad)

    def test_normalises_loose_padding(self) -> None:
        self.assertEqual(A.format_watched("1-2-2020"), "01-02-2020")
        self.assertEqual(A.format_watched("01-02-2020"), "01-02-2020")


class TestResolveIndex(unittest.TestCase):
    def test_find_is_substring_and_case_insensitive(self) -> None:
        self.assertEqual(A.find(BOOKS, "eta"), [1])

    def test_ambiguous_substring_resolves_to_none(self) -> None:
        self.assertIsNone(A.resolve_index(BOOKS, "a"))

    def test_exact_matches_whole_title(self) -> None:
        self.assertEqual(A.resolve_index(BOOKS, "beta", strict=True), 1)

    def test_index_of_requires_exactly_one_hit(self) -> None:
        self.assertEqual(A.index_of(BOOKS, "Beta"), 1)
        with self.assertRaises(LookupError):
            A.index_of(BOOKS, "a")


class TestValidateEntries(SandboxCase):
    def test_clean_entries_pass(self) -> None:
        self.assertEqual(A.validate_entries("books", A.load("books")), [])

    def test_ids_must_be_sequential(self) -> None:
        entries = A.load("books")
        entries[1]["id"] = 7
        self.assertIn("ids not sequential", A.validate_entries("books", entries)[0])

    def test_key_order_drift_is_caught(self) -> None:
        entries = A.load("books")
        entries[0] = {"title": entries[0]["title"], **entries[0]}
        self.assertTrue(
            any("schema drift" in p for p in A.validate_entries("books", entries))
        )

    def test_duplicate_cover_is_caught(self) -> None:
        entries = A.load("books")
        entries[1]["cover_url"] = entries[0]["cover_url"]
        self.assertTrue(
            any(
                "duplicate cover_url" in p for p in A.validate_entries("books", entries)
            )
        )

    def test_bad_rating_is_caught(self) -> None:
        entries = A.load("books")
        entries[0]["rating_text"] = "TBD"
        self.assertTrue(
            any("bad rating" in p for p in A.validate_entries("books", entries))
        )

    def test_movies_must_be_date_sorted(self) -> None:
        entries = A.load("movies")
        entries.reverse()
        self.assertTrue(
            any("not sorted" in p for p in A.validate_entries("movies", entries))
        )


class TestValidateCovers(SandboxCase):
    def test_orphan_cover_is_caught(self) -> None:
        entries = A.load("books")
        (self.root / "assets" / "covers" / "books" / "orphan.webp").write_bytes(b"x")
        problems = A.validate_covers("books", entries)
        self.assertTrue(any("orphan.webp" in p for p in problems))

    def test_missing_cover_is_caught(self) -> None:
        entries = A.load("books")
        (self.root / "assets" / "covers" / "books" / "alpha.webp").unlink()
        problems = A.validate_covers("books", entries)
        self.assertTrue(any("alpha.webp" in p for p in problems))


class TestSaveIsAtomic(SandboxCase):
    def test_invalid_data_never_reaches_disk(self) -> None:
        before = self.read("movies")
        entries = A.load("movies")
        entries.reverse()
        with self.assertRaises(AssertionError):
            A.save("movies", entries)
        self.assertEqual(self.read("movies"), before)

    def test_valid_data_is_written(self) -> None:
        entries = A.load("books")
        entries[0]["rating_text"] = "10/10"
        A.save("books", entries)
        self.assertEqual(A.load("books")[0]["rating_text"], "10/10")

    def test_no_temp_file_is_left_behind(self) -> None:
        A.save("books", A.load("books"))
        self.assertFalse((self.root / "data" / "books.json.tmp").exists())


class TestReorderCli(SandboxCase):
    def run_reorder(self, **kwargs: object) -> tuple[int, str]:
        defaults: dict[str, object] = dict(
            cat="shows",
            title=None,
            before=None,
            after=None,
            position=None,
            rename=None,
            exact=False,
            sort=None,
            descending=False,
        )
        defaults.update(kwargs)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = reorder_mod.run(Namespace(**defaults))
        return code, buf.getvalue()

    def test_position_down_lands_where_asked(self) -> None:
        code, _ = self.run_reorder(title="Show One", position=3)
        self.assertEqual(code, 0)
        self.assertEqual(self.titles("shows"), ["Show Two", "Show Three", "Show One"])

    def test_position_up_lands_where_asked(self) -> None:
        code, _ = self.run_reorder(title="Show Three", position=1)
        self.assertEqual(code, 0)
        self.assertEqual(self.titles("shows"), ["Show Three", "Show One", "Show Two"])

    def test_before_places_the_entry_against_the_anchor(self) -> None:
        code, _ = self.run_reorder(title="Show One", before="Show Three")
        self.assertEqual(code, 0)
        self.assertEqual(self.titles("shows"), ["Show Two", "Show One", "Show Three"])

    def test_after_places_the_entry_against_the_anchor(self) -> None:
        code, _ = self.run_reorder(title="Show Three", after="Show One")
        self.assertEqual(code, 0)
        self.assertEqual(self.titles("shows"), ["Show One", "Show Three", "Show Two"])

    def test_rename_to_an_existing_title_is_refused(self) -> None:
        code, out = self.run_reorder(title="Show One", rename="Show Two")
        self.assertEqual(code, 1)
        self.assertIn("already used", out)
        self.assertEqual(self.titles("shows"), ["Show One", "Show Two", "Show Three"])

    def test_rename_reports_the_new_id(self) -> None:
        code, out = self.run_reorder(title="Show One", rename="Show Renamed")
        self.assertEqual(code, 0)
        self.assertIn("now id 1", out)
        self.assertEqual(self.titles("shows")[0], "Show Renamed")

    def test_movies_are_not_repositioned(self) -> None:
        code, out = self.run_reorder(cat="movies", title="Movie One", position=2)
        self.assertEqual(code, 1)
        self.assertIn("date_watched", out)
        self.assertEqual(self.titles("movies"), ["Movie One", "Movie Two"])


class TestRateCli(SandboxCase):
    def run_rate(self, **kwargs: object) -> tuple[int, str]:
        defaults: dict[str, object] = dict(
            cat="books",
            title="Alpha",
            exact=False,
            rating="8",
            position=None,
            date=None,
        )
        defaults.update(kwargs)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = rate_mod.run(Namespace(**defaults))
        return code, buf.getvalue()

    def test_rate_in_place(self) -> None:
        code, _ = self.run_rate(rating="9.5")
        self.assertEqual(code, 0)
        self.assertEqual(A.load("books")[0]["rating_text"], "9.5/10")

    def test_position_down_lands_where_asked(self) -> None:
        code, _ = self.run_rate(position=3)
        self.assertEqual(code, 0)
        self.assertEqual(self.titles("books"), ["Beta", "Gamma", "Alpha"])

    def test_movies_refuse_position(self) -> None:
        code, out = self.run_rate(cat="movies", title="Movie One", position=2)
        self.assertEqual(code, 1)
        self.assertIn("date_watched", out)
        self.assertEqual(self.titles("movies"), ["Movie One", "Movie Two"])

    def test_movies_accept_a_date_and_resort(self) -> None:
        code, _ = self.run_rate(cat="movies", title="Movie One", date="05-05-2021")
        self.assertEqual(code, 0)
        self.assertEqual(self.titles("movies"), ["Movie Two", "Movie One"])
        self.assertEqual(A.validate_entries("movies", A.load("movies")), [])

    def test_books_refuse_a_date(self) -> None:
        code, out = self.run_rate(date="05-05-2021")
        self.assertEqual(code, 1)
        self.assertIn("movies only", out)


@unittest.skipUnless(MAGICK, "ImageMagick is needed to read cover dimensions")
class TestAddCli(SandboxCase):
    def setUp(self) -> None:
        super().setUp()
        make_cover(self.root / "assets" / "covers" / "books" / "delta.webp")

    def test_add_reuses_an_existing_cover(self) -> None:
        args = Namespace(
            cat="books",
            title="Delta",
            year=2024,
            rating="8",
            author="D Four",
            date=None,
            slug=None,
            cover="delta.webp",
            cover_url=None,
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = add_mod.run(args)
        self.assertEqual(code, 0)
        self.assertEqual(self.titles("books"), ["Alpha", "Beta", "Gamma", "Delta"])

    def test_add_refuses_a_cover_owned_by_another_entry(self) -> None:
        args = Namespace(
            cat="books",
            title="Delta",
            year=2024,
            rating="8",
            author="D Four",
            date=None,
            slug=None,
            cover="alpha.webp",
            cover_url=None,
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = add_mod.run(args)
        self.assertEqual(code, 1)
        self.assertIn("already the cover", buf.getvalue())

    def test_add_refuses_a_duplicate_title(self) -> None:
        args = Namespace(
            cat="books",
            title="alpha",
            year=2024,
            rating="8",
            author="D Four",
            date=None,
            slug=None,
            cover="delta.webp",
            cover_url=None,
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = add_mod.run(args)
        self.assertEqual(code, 1)
        self.assertIn("already exists", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
