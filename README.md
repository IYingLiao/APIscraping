# How to Run This Code from Command Prompt

## Prerequisites
- Python 3.x installed on your system
- pip (Python package installer)

## Step 1: Install Dependencies

Open Command Prompt and navigate to the project directory:

```cmd
cd C:\Git\APIScrapping2
```

Then install the required packages:

```cmd
pip install -r requirements.txt
```

**Note:** If you plan to use the `lung_cancer_nlp_pipeline.py` script, you'll also need to download a spaCy language model:

```cmd
python -m spacy download en_core_web_sm
```

## Step 2: Navigate to the APIscraping Directory

The main script is in the `APIscraping` folder:

```cmd
cd APIscraping
```

## Step 3: Run the Main Script

### Basic Usage (Required: --query)

The `--query` parameter is required. All other parameters are optional:

```cmd
python main.py --query "your search query here"
```

### Examples

**Example 1: Simple query**
```cmd
python main.py --query "lung cancer"
```

**Example 2: Limit results and specify output directory**
```cmd
python main.py --query "lung cancer" --max-results 50 --out-dir my_output
```

**Example 3: Add your email (recommended by NCBI)**
```cmd
python main.py --query "lung cancer" --email your.email@example.com
```

**Example 4: Skip entity annotations (faster, but no PubTator data)**
```cmd
python main.py --query "lung cancer" --no-entities
```

**Example 5: Full example with all options**
```cmd
python main.py --query "lung cancer" --max-results 200 --batch-size 50 --out-dir data_raw --email your.email@example.com
```

### Available Command-Line Arguments

- `--query` (REQUIRED): Your PubMed search query (e.g., "lung cancer", "diabetes treatment")
- `--max-results` (optional, default=100): Maximum number of articles to fetch
- `--batch-size` (optional, default=100): Number of articles per API request
- `--out-dir` (optional, default="data_raw"): Directory to save the output files
- `--email` (optional): Your email address (recommended by NCBI for API usage)
- `--no-entities` (optional): Skip fetching PubTator entity annotations

## Output

The script will:
1. Search PubMed for articles matching your query
2. Download title and abstract for each article
3. Save each article as `<pmid>.txt` in the output directory
4. Optionally fetch and append entity annotations from PubTator

Each output file will have:
- Line 1: `PMID|t|<title>`
- Line 2: `PMID|a|<abstract>`
- Additional lines (if entities enabled): `PMID<TAB>start<TAB>end<TAB>mention<TAB>type<TAB>id`

## Alternative: Run the NLP Pipeline Script

If you want to use the spaCy-based NLP pipeline instead:

```cmd
python lung_cancer_nlp_pipeline.py --input_dir data_raw --output_dir data_processed
```

This processes existing `.txt` files and adds spaCy entity annotations.
****
