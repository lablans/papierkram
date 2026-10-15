---
name: word-cleanup
description: >
  Clean up the formatting of a Word (.docx) document at XML level: stray whitespace, empty spacer paragraphs, soft line breaks, direct formatting instead of paragraph styles (Absatzvorlagen/Formatvorlagen), fake headings and lists, coloured text, broken links and cross-references. Also: ASCII diff of two .docx versions, layout lint on the real Word render, style comparison of two differently formatted versions. Triggers: "clean up / fix the formatting of this Word file", "inconsistent formatting", "use the Absatzvorlagen", "Formatvorlagen konsistent", "what changed between these two Word files", "compare the formatting".
---

# Word cleanup

Goal: a **minimal set of paragraph styles, followed to the tee**. Direct formatting stays only where it is genuinely required (e.g., a bold word, a highlight, superscript, a deliberate page break).

**Every removal rule below is subject to this triage.** Decide for each piece of direct formatting:
- **debris** → remove (tracked);
- **intentional and recurring** → move it into a style (an existing one, or propose a new one and ask);
- **intentional one-off that a style cannot express** (page break before a chapter, keep-with-next on a figure, a centered figure) → keep it and list it in the report.

If unsure which applies, ask.

Toolkit: `wordtool.py` in this directory, a command line and a library that per-document transforms import. Below, `W` stands for `python3 -I .claude/skills/word-cleanup/wordtool.py`; `W --help` and `W <command> --help` list the commands and their arguments. Ask the user to install any missing dependency.

## Workflow

1. Load `anthropic-skills:docx` (repo rule). Its `scripts/office/validate.py`, found under the base directory announced when the skill loads, is part of the verification gate.
2. `W unpack <file.docx> <dir>`.
3. **Audit:** `W audit <dir>`, `W lint <file.docx> <outdir>` (needs Word closed; ask the user) and a paragraph-by-paragraph read of the text. If there are pending tracked changes or comments from others, ask whether they should be accepted first.
4. **Report:** numbered findings, worst first, then the open questions with a proposed default for each (see below). Split them into formatting (to fix) and content (report only).
5. **Transform:** write a per-document script in the scratchpad that imports the toolkit: `sys.path.insert(0, '<repo>/.claude/skills/word-cleanup')`. Never put the downloaded directory on the path. Anchor every hand-picked paragraph with a text assertion, so the script refuses to run on another version. For a handful of edits, the Edit tool on the XML is fine. Pack with `W pack`.
6. **Verification gate:** `W check <orig.docx> <new.docx> <outdir> <validate.py> "<author>"`. Every item must pass:
   - reject view equals the original for every part, and the accept-view text diff contains only the intended edits;
   - `validate.py` passes;
   - the ASCII diff (`<outdir>/diff.txt`) contains only intended changes, including the untracked ones (styles, numbering, settings). Show the user its relevant part or a faithful summary; it is their way to check what was changed without trusting the tracked changes alone;
   - `lint` on the result: no new layout issues, and every remaining one explained.
7. **Visual check:** look at the rendered pages your changes touch, plus the TOC. The XML checks cannot see layout problems. Do not deliver before this.
8. **Review page** (offer it for any non-trivial cleanup): a before/after Artifact, one representative example per type of change.
   - Scripts do the deterministic part: `W render` both versions, `W crop` with a spec of anchor texts, and the diff for the page's "changes" box.
   - You do the judgement: which places represent each type of change, the captions (what changed, how many places, pages), a list of changes that are invisible in a page image, and any regression the render reveals. Load the artifact skills before writing the page; publish crops as files next to the page.
9. Tell the user: on opening, answer "update fields" with Yes, review, then Accept All.

## Other uses

- **What changed between two versions** (e.g. a co-author's edit): `W diff <dir_a> <dir_b>`.
- **Layout check only:** `W lint <file.docx> <outdir>`: number-to-text gaps per text size (a style indent too small or inconsistent), stretched lines, headings stranded at the page end, field error text, fonts in the PDF, raster images with their dpi.
- **Style comparison** of two versions with the same content: `W stylecompare <dir_a> <dir_b>`: paragraph styles A → B, direct and character formatting only in one of them, differing style definitions.

## Settled preferences (apply without asking)

- **XML only.** Never use LibreOffice/soffice, not even for viewing: it introduces new formatting problems and does not render like Word. Visual checks go through real Word (`W render`).
- **Track every change** under the name "Magic Word Cleanup". Style definitions, numbering definitions and settings cannot be tracked: list those changes in the report. Never create no-op revisions.
- **Whitespace:** no leading, trailing or double spaces. No empty paragraphs as spacers. No soft line breaks (Shift+Enter) used as paragraph breaks in body text; inside table cells they are fine. A soft break plus spaces usually hides a lost paragraph break, so restore it.
- **Headings:** a bold Normal paragraph acting as a heading becomes the *existing* heading style one level below its parent heading, never a new style. Typed numbers ("6.3", "6. 2 ") are deleted and automatic numbering re-enabled (remove `numId 0` overrides). Unnumbered sub-items under a numbered heading also become the next heading level. A heading style's hanging indent must fit its widest number.
- **Lists:** typed markers ("i) ii)", "- ") become a real list, except in deliberately quoted text (e.g. a copied legal clause), which keeps its original markers. All bullet lists share one numbering definition.
- **Body text:** Normal (Standard). Triage (see top) all direct spacing, alignment, indents, borders (including "none" borders), line spacing and "Normal (Web)".
- **Additional styles, each with an English `w:name` and the German name as `w:aliases`:**
  - "Table Text" / Tabellentext: 10 pt, left, no spacing, used for all table cells.
  - "Subheading" / Zwischenüberschrift: bold, keep with next, for label lines that stand alone ("Risk:"). Labels that run into their sentence stay bold runs in Normal.
  - "List Lead-in" / Listeneinleitung: keep with next, for the sentence introducing a list.
- **Tables:** black and white: no coloured fills or text; the header row is set off by bold and repeats on each page.
- **Colour:** text is black unless there is a specific reason; header/footer grey belongs in the header/footer styles. **Keep highlights**: they are intentional markers.
- **Graphics:** vector (SVG or EMF), so they print sharp and keep selectable text in the PDF. Report every raster figure with its effective dpi and ask for the vector source; never rasterize anything.
- **Character formatting:** strip direct fonts, sizes and "auto" colour, after the triage (see top): an intentional font, e.g. monospace for code or file names, goes into a character style instead. Keep bold, italic, underline, super/subscript, character styles and highlights. Bold covers the label word only (no bold colon, unless the whole group of labels does it consistently), never stray spaces.
- **Broken links and references are repaired:** an empty `w:hyperlink` loses its link wrapper and keeps its text; a REF to a missing bookmark gets its bookmark (e.g. on the caption).
- **Unused styles are deleted.** Keep any style that a pending revision still references.
- **Content is reported, never changed** without explicit approval. This covers wrong or hard-coded cross-references, typos, garbled text and inconsistent product names. Offer to convert typed cross-references into REF fields.

## Ask each time (with a default)

- Title page: usually leave it alone if it renders correctly.
- Proofing language. Default: the document default; mixed `w:lang` overrides are removed.
- Annex and front-matter headings (numbered chapter vs. unnumbered annex style; check the TOC `\t` switch for the style it expects).
- A dedicated bullet/number list style, so list paragraphs carry no direct `numPr`.
- Removals that change nothing visible (complex-script font, `lang` equal to the default, `color auto`, "none" borders): track them or apply silently? Tracked, they show up as noisy "Formatiert" balloons in Word.
- Content findings (problems in the text itself: wrong cross-references, typos, debris, inconsistent names, stale dates): report in the chat only (default), or also as Word comments in the document (docx skill's `comment.py`) so co-authors see them in place?

## Tools from the docx skill

- `scripts/office/validate.py`: use (verification gate). Never `--auto-repair` the deliverable; only a copy, and inspect what it changed.
- `scripts/accept_changes.py`: forbidden (runs through LibreOffice).
- `scripts/office/soffice.py` and its PDF/image "verify the output" step: forbidden; use `W render`.
- `scripts/merge_runs.py`: do not use. It rewrites runs without tracking, and `chars()` already reads text across runs.
- `scripts/comment.py`: only when the user wants content findings as Word comments.
- `pandoc`: fine for reading (with `--track-changes=all`), but it collapses multiple spaces, so whitespace findings must come from `W audit`.

## Word pitfalls (learned the hard way)

- **Paragraph indices:** regex-based paragraph splitting swallows childless `<w:p/>`, so the indices drift. Always index with lxml (`body.iter(w:p)`).
- **Style IDs are localized** and change between saves: a save by Word with another interface language renames them all (`berschrift1` → `Heading1`). Resolve built-in styles by `w:name` ("heading 1", "list paragraph", "toc 1", "caption") via `style_ids()`, never by ID.
- **Spurious revisions:** a detached `deepcopy` serializes namespace declarations, so a naive before/after comparison records a revision for every run. `Redline` compares c14n of copies on both sides.
- **Fields:** never edit inside field instructions or results. `chars()` protects them; Word regenerates them anyway.
- **Paragraph merges:**
  - A deleted paragraph mark merges the paragraph into the *next* one, and it is unclear whose properties survive. Choose the direction so that a heading never takes part: for an empty paragraph after body text, delete the mark of the body paragraph in front of it. If it sits between two headings, give it the following heading's style first.
  - Never mark the same paragraph twice; that is a schema error.
- **Split paragraphs** (`Redline.split_after`) must not copy `w14:paraId`.
- **Field errors:** Word turns an empty `w:hyperlink` into a HYPERLINK field. When fields update, that field and any REF to a missing bookmark show "Fehler! …" / "Error! …". Saving then bakes the error text into the document. So fix broken links and bookmarks *before* setting `w:updateFields` (settings.xml, before `w:hdrShapeDefaults`). Word drops that setting on save.
- **Heading numbers in Word's PDF** are often not extractable as text (pdftotext misses them), so `lint` measures number gaps on the rendered pixels.
- **Packing:** use `W pack`: it keeps the original archive's entry order (`[Content_Types].xml` first) and needs no external tool.
- **Element order:** pPr/rPr children are schema-ordered. Use `insert_ordered`, never `append`, and keep `rPrChange`/`pPrChange` last.
