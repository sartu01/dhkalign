#!/usr/bin/env python3
"""
DHK Align Dataset Fixer and Processor
Fixes duplicate columns, validates data, and generates production-ready outputs
"""

import pandas as pd
import numpy as np
import json
import hashlib
import re
from typing import Dict, List, Tuple
import sys

class DHKDatasetProcessor:
    def __init__(self):
        self.stats = {
            'total_rows': 0,
            'valid_rows': 0,
            'duplicates_removed': 0,
            'fixed_columns': 0,
            'missing_values_filled': 0,
            'encoding_fixes': 0
        }
        self.issues = []
        
    def process_dataset(self, input_file: str, output_prefix: str):
        """Main processing pipeline"""
        print("🚀 DHK Align Dataset Processing Started\n")
        
        # Step 1: Load and fix CSV structure
        df = self.load_and_fix_csv(input_file)
        
        # Step 2: Clean and validate data
        df_clean = self.clean_dataset(df)
        
        # Step 3: Enrich with computed fields
        df_enriched = self.enrich_dataset(df_clean)
        
        # Step 4: Generate outputs
        self.generate_outputs(df_enriched, output_prefix)
        
        # Step 5: Print report
        self.print_report()
        
    def load_and_fix_csv(self, file_path: str) -> pd.DataFrame:
        """Load CSV and fix structural issues"""
        print("📂 Loading CSV and fixing structure...")
        
        # Read CSV
        df = pd.read_csv(file_path, encoding='utf-8')
        self.stats['total_rows'] = len(df)
        
        print(f"   Found {len(df)} rows, {len(df.columns)} columns")
        print(f"   Columns: {list(df.columns)}")
        
        # Fix duplicate columns
        column_mapping = {}
        seen_columns = set()
        
        for col in df.columns:
            # Clean column name
            clean_col = col.strip().lower().replace(' ', '_')
            
            # Handle duplicates
            if clean_col in seen_columns:
                if 'unnamed' in col.lower():
                    continue  # Skip unnamed columns
                else:
                    # Keep the first occurrence
                    column_mapping[col] = f"{clean_col}_duplicate"
                    self.issues.append(f"Duplicate column found: {col}")
            else:
                column_mapping[col] = clean_col
                seen_columns.add(clean_col)
        
        # Rename columns
        df = df.rename(columns=column_mapping)
        
        # Drop unnamed columns
        unnamed_cols = [col for col in df.columns if 'unnamed' in col.lower()]
        if unnamed_cols:
            df = df.drop(columns=unnamed_cols)
            self.stats['fixed_columns'] += len(unnamed_cols)
            print(f"   Dropped {len(unnamed_cols)} unnamed columns")
        
        # Handle duplicate columns by keeping first non-null value
        final_columns = {}
        for col in df.columns:
            base_col = col.replace('_duplicate', '')
            if base_col not in final_columns:
                final_columns[base_col] = df[col]
            else:
                # Merge duplicates by taking non-null values
                final_columns[base_col] = df[col].fillna(final_columns[base_col])
                self.stats['fixed_columns'] += 1
        
        # Create cleaned dataframe
        df_clean = pd.DataFrame(final_columns)
        
        # Add missing audience column if not present
        if 'audience' not in df_clean.columns:
            df_clean['audience'] = 'general'
            self.issues.append("Missing 'audience' column - added with default 'general'")
        
        print(f"✅ Fixed structure: {len(df_clean.columns)} columns")
        print(f"   Final columns: {list(df_clean.columns)}")
        
        return df_clean
        
    def clean_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate dataset"""
        print("\n🧹 Cleaning dataset...")
        
        # Required columns
        required_cols = ['id', 'input_text', 'output_text', 'direction', 
                        'tone', 'audience', 'cultural_context']
        
        # Check for missing columns
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Create a copy for cleaning
        df_clean = df.copy()
        
        # Fix IDs
        df_clean['id'] = range(1, len(df_clean) + 1)
        
        # Clean text fields
        for text_col in ['input_text', 'output_text']:
            df_clean[text_col] = df_clean[text_col].apply(self.clean_text)
        
        # Remove rows with empty input/output
        before_rows = len(df_clean)
        df_clean = df_clean.dropna(subset=['input_text', 'output_text'])
        df_clean = df_clean[
            (df_clean['input_text'].str.strip() != '') & 
            (df_clean['output_text'].str.strip() != '')
        ]
        removed_empty = before_rows - len(df_clean)
        if removed_empty > 0:
            self.issues.append(f"Removed {removed_empty} rows with empty text")
        
        # Remove duplicates based on input_text
        before_dedup = len(df_clean)
        df_clean = df_clean.drop_duplicates(subset=['input_text'], keep='first')
        self.stats['duplicates_removed'] = before_dedup - len(df_clean)
        
        # Normalize categorical fields
        df_clean['direction'] = df_clean['direction'].apply(self.normalize_direction)
        df_clean['tone'] = df_clean['tone'].apply(self.normalize_tone)
        df_clean['audience'] = df_clean['audience'].apply(self.normalize_audience)
        df_clean['cultural_context'] = df_clean['cultural_context'].fillna('general')
        
        self.stats['valid_rows'] = len(df_clean)
        print(f"✅ Cleaned: {self.stats['valid_rows']} valid rows")
        
        return df_clean
        
    def clean_text(self, text) -> str:
        """Clean text while preserving Bengali characters"""
        if pd.isna(text):
            return ""
            
        text = str(text).strip()
        
        # Fix common encoding issues
        replacements = {
            '"': '"', '"': '"', ''': "'", ''': "'",
            '–': '-', '—': '-', '…': '...',
            '\u200b': '', '\u200c': '', '\u200d': '',  # Zero-width characters
            '\ufeff': '',  # BOM
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
            
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text
        
    def normalize_direction(self, direction) -> str:
        """Normalize direction values"""
        if pd.isna(direction):
            return 'banglish_to_english'
            
        direction = str(direction).lower().strip()
        
        mappings = {
            'banglish to english': 'banglish_to_english',
            'english to banglish': 'english_to_banglish',
            'bengali to english': 'bengali_to_english',
            'english to bengali': 'english_to_bengali',
            'b2e': 'banglish_to_english',
            'e2b': 'english_to_banglish'
        }
        
        return mappings.get(direction, 'banglish_to_english')
        
    def normalize_tone(self, tone) -> str:
        """Normalize tone values"""
        if pd.isna(tone):
            return 'neutral'
            
        tone = str(tone).lower().strip()
        
        valid_tones = ['formal', 'informal', 'casual', 'professional', 
                      'friendly', 'neutral', 'respectful']
        
        # Map common variations
        tone_map = {
            'polite': 'respectful',
            'business': 'professional',
            'friend': 'friendly',
            'normal': 'neutral'
        }
        
        tone = tone_map.get(tone, tone)
        
        return tone if tone in valid_tones else 'neutral'
        
    def normalize_audience(self, audience) -> str:
        """Normalize audience values"""
        if pd.isna(audience):
            return 'general'
            
        audience = str(audience).lower().strip()
        
        valid_audiences = ['general', 'youth', 'professional', 'academic', 
                          'elderly', 'children', 'formal']
        
        # Map variations
        audience_map = {
            'young': 'youth',
            'kids': 'children',
            'old': 'elderly',
            'student': 'academic',
            'business': 'professional'
        }
        
        audience = audience_map.get(audience, audience)
        
        return audience if audience in valid_audiences else 'general'
        
    def detect_language(self, text: str) -> str:
        """Detect the language of text"""
        bengali_pattern = re.compile(r'[\u0980-\u09FF]')
        english_pattern = re.compile(r'[a-zA-Z]')
        
        has_bengali = bool(bengali_pattern.search(text))
        has_english = bool(english_pattern.search(text))
        
        if has_bengali and has_english:
            return 'mixed'
        elif has_bengali:
            return 'bengali'
        elif has_english:
            # Check for Banglish
            banglish_words = {'ami', 'tumi', 'apni', 'keno', 'ki', 'kemon', 
                            'bhalo', 'achi', 'tomar', 'amar', 'korbo', 'jabo'}
            text_lower = text.lower()
            word_set = set(text_lower.split())
            
            if len(word_set.intersection(banglish_words)) >= 2:
                return 'banglish'
            else:
                return 'english'
                
        return 'unknown'
        
    def enrich_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add computed fields and enrichments"""
        print("\n🔬 Enriching dataset...")
        
        # Language detection
        df['input_language'] = df['input_text'].apply(self.detect_language)
        df['output_language'] = df['output_text'].apply(self.detect_language)
        
        # Text metrics
        df['input_length'] = df['input_text'].str.len()
        df['output_length'] = df['output_text'].str.len()
        df['input_words'] = df['input_text'].str.split().str.len()
        df['output_words'] = df['output_text'].str.split().str.len()
        
        # Ratios
        df['length_ratio'] = df['output_length'] / df['input_length'].replace(0, 1)
        df['word_ratio'] = df['output_words'] / df['input_words'].replace(0, 1)
        
        # Pattern detection
        df['has_question'] = df['input_text'].str.contains(r'\?$', regex=True)
        df['has_exclamation'] = df['input_text'].str.contains(r'!$', regex=True)
        df['is_greeting'] = df['input_text'].str.lower().str.contains(
            r'^(hi|hello|hey|namaste|assalamualaikum|salam)', regex=True
        )
        
        # Cultural markers
        cultural_terms = ['dada', 'didi', 'bhai', 'bon', 'mama', 'khala', 
                         'nana', 'nani', 'puja', 'eid', 'iftar', 'bhabi']
        
        df['has_cultural_term'] = df['input_text'].str.lower().apply(
            lambda x: any(term in x for term in cultural_terms)
        )
        
        # Complexity score (0-1)
        df['complexity'] = (
            df['input_words'] / 20 * 0.3 +
            df['input_length'] / 100 * 0.3 +
            df['has_cultural_term'].astype(int) * 0.2 +
            (df['input_language'] == 'mixed').astype(int) * 0.2
        ).clip(0, 1)
        
        print(f"✅ Enriched with {len(df.columns) - 7} computed fields")
        
        return df
        
    def generate_outputs(self, df: pd.DataFrame, output_prefix: str):
        """Generate all output files"""
        print("\n📁 Generating output files...")
        
        # 1. Full JSON dataset
        full_data = {
            'metadata': {
                'version': '1.0.0',
                'total_entries': len(df),
                'generated_at': pd.Timestamp.now().isoformat(),
                'statistics': self.calculate_statistics(df)
            },
            'translations': df.to_dict('records')
        }
        
        with open(f'{output_prefix}_full.json', 'w', encoding='utf-8') as f:
            json.dump(full_data, f, ensure_ascii=False, indent=2)
        
        # 2. Lookup tables for fast access
        lookup_tables = self.generate_lookup_tables(df)
        with open(f'{output_prefix}_lookup.json', 'w', encoding='utf-8') as f:
            json.dump(lookup_tables, f, ensure_ascii=False, indent=2)
        
        # 3. Client bundle (minimal)
        client_bundle = self.generate_client_bundle(df)
        with open(f'{output_prefix}_client.json', 'w', encoding='utf-8') as f:
            json.dump(client_bundle, f, ensure_ascii=False)
        
        # 4. CSV with all enrichments
        df.to_csv(f'{output_prefix}_enriched.csv', index=False, encoding='utf-8')
        
        # 5. Validation report
        self.generate_report(df, f'{output_prefix}_report.txt')
        
        print(f"✅ Generated 5 output files with prefix: {output_prefix}")
        
    def calculate_statistics(self, df: pd.DataFrame) -> Dict:
        """Calculate dataset statistics"""
        stats = {
            'by_direction': df['direction'].value_counts().to_dict(),
            'by_tone': df['tone'].value_counts().to_dict(),
            'by_audience': df['audience'].value_counts().to_dict(),
            'by_input_language': df['input_language'].value_counts().to_dict(),
            'avg_input_length': float(df['input_length'].mean()),
            'avg_output_length': float(df['output_length'].mean()),
            'avg_complexity': float(df['complexity'].mean()),
            'total_unique_words': len(set(' '.join(df['input_text']).lower().split()))
        }
        
        return stats
        
    def generate_lookup_tables(self, df: pd.DataFrame) -> Dict:
        """Generate optimized lookup tables"""
        tables = {
            'exact': {},      # Exact phrase matches
            'words': {},      # Single word translations
            'patterns': [],   # Common patterns
            'cultural': {}    # Cultural specific terms
        }
        
        for _, row in df.iterrows():
            key = row['input_text'].lower()
            
            # Exact matches
            if key not in tables['exact']:
                tables['exact'][key] = {
                    'output': row['output_text'],
                    'tone': row['tone'],
                    'audience': row['audience'],
                    'complexity': row['complexity']
                }
            
            # Single words
            if row['input_words'] == 1:
                tables['words'][key] = row['output_text']
            
            # Cultural terms
            if row['has_cultural_term']:
                tables['cultural'][key] = {
                    'output': row['output_text'],
                    'context': row['cultural_context']
                }
        
        return tables
        
    def generate_client_bundle(self, df: pd.DataFrame) -> Dict:
        """Generate minimal client-side bundle"""
        # Select most common, simple translations
        simple_df = df[
            (df['complexity'] < 0.5) & 
            (df['input_words'] <= 5)
        ].nsmallest(200, 'input_words')
        
        bundle = {
            'v': '1.0',
            't': {}
        }
        
        for _, row in simple_df.iterrows():
            bundle['t'][row['input_text'].lower()] = row['output_text']
        
        return bundle
        
    def generate_report(self, df: pd.DataFrame, output_file: str):
        """Generate detailed validation report"""
        report = []
        
        report.append("="*60)
        report.append("DHK ALIGN DATASET VALIDATION REPORT")
        report.append("="*60)
        report.append(f"Generated: {pd.Timestamp.now()}")
        report.append("")
        
        report.append("SUMMARY STATISTICS:")
        report.append(f"  Total rows processed: {self.stats['total_rows']}")
        report.append(f"  Valid rows: {self.stats['valid_rows']}")
        report.append(f"  Duplicates removed: {self.stats['duplicates_removed']}")
        report.append(f"  Columns fixed: {self.stats['fixed_columns']}")
        report.append(f"  Success rate: {(self.stats['valid_rows']/self.stats['total_rows']*100):.1f}%")
        report.append("")
        
        if self.issues:
            report.append("ISSUES FOUND:")
            for issue in self.issues[:20]:
                report.append(f"  - {issue}")
            if len(self.issues) > 20:
                report.append(f"  ... and {len(self.issues)-20} more")
            report.append("")
        
        stats = self.calculate_statistics(df)
        
        report.append("DATASET COMPOSITION:")
        report.append("  Direction distribution:")
        for direction, count in stats['by_direction'].items():
            pct = count / len(df) * 100
            report.append(f"    {direction}: {count} ({pct:.1f}%)")
        
        report.append("\n  Tone distribution:")
        for tone, count in stats['by_tone'].items():
            pct = count / len(df) * 100
            report.append(f"    {tone}: {count} ({pct:.1f}%)")
        
        report.append("\n  Language detection:")
        for lang, count in stats['by_input_language'].items():
            pct = count / len(df) * 100
            report.append(f"    {lang}: {count} ({pct:.1f}%)")
        
        report.append("\nQUALITY METRICS:")
        report.append(f"  Average input length: {stats['avg_input_length']:.1f} chars")
        report.append(f"  Average output length: {stats['avg_output_length']:.1f} chars")
        report.append(f"  Average complexity: {stats['avg_complexity']:.3f}")
        report.append(f"  Unique input words: {stats['total_unique_words']}")
        
        # Find outliers
        outliers = df[
            (df['length_ratio'] > 3) | (df['length_ratio'] < 0.3)
        ]
        
        if len(outliers) > 0:
            report.append(f"\nOUTLIERS (unusual length ratios): {len(outliers)} entries")
            for _, row in outliers.head(5).iterrows():
                report.append(f"  '{row['input_text'][:30]}...' → ratio: {row['length_ratio']:.2f}")
        
        # Coverage gaps
        report.append("\nCOVERAGE ANALYSIS:")
        
        # Check for missing common phrases
        common_phrases = ['ki koro', 'kemon acho', 'kothai jachcho', 'ki khabo']
        missing = []
        for phrase in common_phrases:
            if not df['input_text'].str.lower().str.contains(phrase).any():
                missing.append(phrase)
        
        if missing:
            report.append("  Missing common phrases:")
            for phrase in missing:
                report.append(f"    - {phrase}")
        
        report.append("\nRECOMMENDATIONS:")
        report.append("  1. Add more youth/informal tone examples (currently low)")
        report.append("  2. Include more question patterns")
        report.append("  3. Add pronunciation guides for cultural terms")
        report.append("  4. Validate translations with native speakers")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
            
    def print_report(self):
        """Print summary to console"""
        print("\n" + "="*60)
        print("PROCESSING COMPLETE!")
        print("="*60)
        print(f"✅ Valid entries: {self.stats['valid_rows']}/{self.stats['total_rows']}")
        print(f"🔁 Duplicates removed: {self.stats['duplicates_removed']}")
        print(f"🔧 Columns fixed: {self.stats['fixed_columns']}")
        print(f"⚠️  Issues found: {len(self.issues)}")
        print(f"📊 Success rate: {(self.stats['valid_rows']/self.stats['total_rows']*100):.1f}%")


def main():
    """Run the processor"""
    processor = DHKDatasetProcessor()
    
    # Process the dataset
    processor.process_dataset(
        'merged_output.csv',
        'dhk_align_data'
    )
    
    print("\n✨ Dataset processing complete!")
    print("Check the generated files:")
    print("  - dhk_align_data_full.json (complete dataset)")
    print("  - dhk_align_data_lookup.json (optimized lookups)")
    print("  - dhk_align_data_client.json (client bundle)")
    print("  - dhk_align_data_enriched.csv (enriched CSV)")
    print("  - dhk_align_data_report.txt (validation report)")


if __name__ == "__main__":
    main()
