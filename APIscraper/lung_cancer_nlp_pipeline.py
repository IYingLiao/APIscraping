# Reference - this script involves the use of Cursor AI https://cursor.com

"""
Simple local NLP pipeline to generate delirium-style output files
for lung cancer abstracts in `data_raw_lung/`, **without** reading
any delirium annotation files.

Layout of the output matches the delirium `.txt` files:
- Line 1: pmid|t|Title...
- Line 2: pmid|a|Abstract...
- Then one line per detected entity:
    pmid<TAB>start<TAB>end<TAB>text<TAB>type<TAB>ID

Where:
- `type` is taken from spaCy's NER label (e.g. ORG, GPE, DATE, etc.)
- `ID` is set to \"NA\" (no ontology lookup is done here)
"""

import argparse
from pathlib import Path

import spacy


def load_nlp(model: str = "en_core_web_sm"):
    """
    Load the spaCy NLP model once.
    """
    return spacy.load(model)


def process_note_file(
    nlp,
    input_path: Path,
    output_path: Path,
) -> None:
    """
    Read a lung cancer note file in delirium format and write a processed file.

    Input (data_raw_lung):
      pmid|t|Title...
      pmid|a|Abstract...

    Output (data_processed_lung):
      - copy title line
      - copy abstract line
      - entity lines (spaCy NER, format-compatible with delirium):
          pmid  start  end  text  type  ID(=NA)
    """
    lines = input_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    if len(lines) < 2:
        print(f"Skipping {input_path}: not enough lines for title/abstract")
        return

    title_line = lines[0].strip()
    abstract_line = lines[1].strip()

    try:
        pmid_t, flag_t, _title_text = title_line.split("|", 2)
        pmid_a, flag_a, abstract_text = abstract_line.split("|", 2)
    except ValueError:
        print(f"Skipping {input_path}: unexpected line format")
        return

    if pmid_t != pmid_a:
        print(f"WARNING: pmid mismatch in {input_path}: {pmid_t} vs {pmid_a}")
    pmid = pmid_t

    # Run NER on the abstract text
    doc = nlp(abstract_text)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as out:
        # Preserve title and abstract lines as-is
        out.write(f"{title_line}\n")
        out.write(f"{abstract_line}\n")

        # Emit entities in delirium-compatible column layout
        for ent in doc.ents:
            start = ent.start_char
            end = ent.end_char
            ent_text = ent.text.replace("\t", " ").replace("\n", " ")
            etype = ent.label_  # spaCy label
            eid = "NA"          # no ontology mapping in this simple pipeline
            out.write(
                f"{pmid}\t{start}\t{end}\t{ent_text}\t{etype}\t{eid}\n"
            )


def process_directory(
    input_dir: Path,
    output_dir: Path,
    spacy_model: str,
) -> None:
    """
    For each .txt file in `input_dir`, parse title/abstract and run
    spaCy NER, writing results into `output_dir`.
    """
    nlp = load_nlp(spacy_model)

    txt_files = sorted(input_dir.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in {input_dir}")
        return

    print(f"Found {len(txt_files)} .txt files in {input_dir}")
    for f in txt_files:
        out_path = output_dir / f.name
        print(f"Processing {f} -> {out_path}")
        try:
            process_note_file(nlp, f, out_path)
        except Exception as exc:  # pragma: no cover - simple CLI feedback
            print(f"  Failed for {f}: {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a simple NLP pipeline over lung cancer notes in data_raw_lung/ "
            "to produce delirium-style text outputs."
        )
    )
    parser.add_argument(
        "--input_dir",
        type=str,
        default="data_raw_lung",
        help="Directory with raw .txt notes (default: data_raw_lung)",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="data_processed_lung",
        help=(
            "Directory to write delirium-style output files "
            "(default: data_processed_lung)"
        ),
    )
    parser.add_argument(
        "--spacy_model",
        type=str,
        default="en_core_web_sm",
        help="spaCy model name (default: en_core_web_sm)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    process_directory(
        input_dir=input_dir,
        output_dir=output_dir,
        spacy_model=args.spacy_model,
    )


if __name__ == "__main__":
    main()
    
# end of the reference

