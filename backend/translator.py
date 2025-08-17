"""
Enhanced translator.py - WRAITH COMPLETE VERSION
All print() statements replaced with structured logging for production readiness.
"""

import re
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict
from fastapi import APIRouter, Query, HTTPException, Request
from fastapi.responses import JSONResponse

# Import logging system
from backend.utils.logger import logger, log_execution_time, log_api_request

# Initialize router
router = APIRouter()

# Configuration
FEEDBACK_DATA_PATH = "feedback_data.json"

class EnhancedTranslationEngine:
    """
    Claude's 7-step enhanced translation engine with complete structured logging
    """
    
    def __init__(self, db_lookup_func=None):
        """Initialize with database lookup function and logging"""
        self.db_lookup = db_lookup_func or self._dummy_lookup
        
        # Load enhancement components
        self.slang_map = self._build_slang_map()
        self.pattern_matchers = self._build_pattern_matchers()
        self.compound_rules = self._build_compound_rules()
        self.adaptive_cache = self._load_adaptive_cache()
        
        # Initialize empty indices (would be built from database)
        self.word_weights = {}
        self.ngram_index = {}
        
        # Log engine initialization
        logger.info("Enhanced translation engine initialized",
                   event_type="translation_engine_init",
                   slang_mappings=len(self.slang_map),
                   pattern_matchers=len(self.pattern_matchers),
                   compound_rules=len(self.compound_rules),
                   adaptive_cache_size=len(self.adaptive_cache),
                   status="ready")
    
    def _dummy_lookup(self, query: str, direction: str) -> Optional[Dict]:
        """Dummy lookup with logging for testing"""
        dummy_translations = {
            "kemon acho": "how are you",
            "ami tomake bhalo bashi": "I love you", 
            "ki koro": "what are you doing",
            "dhonnobad": "thank you",
            "bhalo achi": "I am fine",
            "tumi": "you",
            "ami": "I",
            "bari": "home",
            "mach": "fish",
            "boro": "big",
            "choto": "small"
        }
        
        result = dummy_translations.get(query.lower())
        if result and direction == "banglish_to_english":
            logger.debug("Dummy lookup successful",
                        event_type="dummy_lookup",
                        query_length=len(query),
                        direction=direction,
                        result_found=True)
            return {"english": result}
        
        logger.debug("Dummy lookup miss",
                    event_type="dummy_lookup", 
                    query_length=len(query),
                    direction=direction,
                    result_found=False)
        return None
    
    def _build_slang_map(self) -> Dict[str, str]:
        """Build slang normalization map with logging"""
        slang_map = {
            # English slang
            'gonna': 'going to', 'wanna': 'want to', 'gotta': 'got to',
            'kinda': 'kind of', 'sorta': 'sort of', 'u': 'you', 
            'ur': 'your', 'r': 'are', 'n': 'and', 'cuz': 'because',
            'plz': 'please', 'thx': 'thanks', 'tho': 'though',
            
            # Banglish specific
            'k': 'ki', 'kmn': 'kemon', 'amr': 'amar', 'tmr': 'tomar',
            'apnr': 'apnar', 'kemon': 'kemon',
        }
        
        logger.debug("Slang normalization map built",
                    event_type="slang_map_init",
                    total_mappings=len(slang_map),
                    english_slang=len([k for k in slang_map.keys() if k in ['gonna', 'wanna', 'u', 'ur']]),
                    banglish_slang=len([k for k in slang_map.keys() if k in ['k', 'kmn', 'amr']]))
        return slang_map
    
    def _build_pattern_matchers(self) -> List[Dict[str, Any]]:
        """Build pattern matching rules with logging"""
        patterns = [
            {
                'name': 'question_ki',
                'pattern': re.compile(r'^(.+?)\s+(ki|k)\s*\?*$', re.IGNORECASE),
                'transform': lambda match, base: f"what {base}?",
                'confidence': 0.85
            },
            {
                'name': 'question_keno',
                'pattern': re.compile(r'^(.+?)\s+(keno|kno)\s*\?*$', re.IGNORECASE),
                'transform': lambda match, base: f"why {base}?",
                'confidence': 0.85
            },
            {
                'name': 'question_kothay',
                'pattern': re.compile(r'^(.+?)\s+(kothay|kothy)\s*\?*$', re.IGNORECASE),
                'transform': lambda match, base: f"where {base}?",
                'confidence': 0.85
            },
            {
                'name': 'question_kokhon',
                'pattern': re.compile(r'^(.+?)\s+(kokhon|kkhon)\s*\?*$', re.IGNORECASE),
                'transform': lambda match, base: f"when {base}?",
                'confidence': 0.85
            },
            {
                'name': 'possession_amar',
                'pattern': re.compile(r'^(amar|amr)\s+(.+?)(\s+ache|\s+ase)*$', re.IGNORECASE),
                'transform': lambda match, base: f"my {base}" if not match.group(3) else f"I have {base}",
                'confidence': 0.80
            },
            {
                'name': 'future_tense_korbo',
                'pattern': re.compile(r'^(ami|i)\s+(.+?)\s+(korbo|krbo)$', re.IGNORECASE),
                'transform': lambda match, base: f"I will {base}",
                'confidence': 0.82
            },
            {
                'name': 'future_tense_korbe',
                'pattern': re.compile(r'^(tumi|you)\s+(.+?)\s+(korbe|krbe)$', re.IGNORECASE),
                'transform': lambda match, base: f"you will {base}",
                'confidence': 0.82
            },
            {
                'name': 'negation_na',
                'pattern': re.compile(r'^(.+?)\s+(na|nai|nei)$', re.IGNORECASE),
                'transform': lambda match, base: f"{base} not" if base.strip() else "not",
                'confidence': 0.75
            }
        ]
        
        pattern_names = [p['name'] for p in patterns]
        logger.debug("Pattern matchers built",
                    event_type="pattern_matcher_init",
                    total_patterns=len(patterns),
                    pattern_types=pattern_names,
                    confidence_range=f"{min(p['confidence'] for p in patterns)}-{max(p['confidence'] for p in patterns)}")
        return patterns
    
    def _build_compound_rules(self) -> List[Dict[str, Any]]:
        """Build compound word rules with logging"""
        rules = [
            {
                'pattern': re.compile(r'(\w+)(bari|ghor)$', re.IGNORECASE),
                'split': lambda match: [match.group(1), match.group(2)],
                'description': 'house/building compounds'
            },
            {
                'pattern': re.compile(r'(\w+)(mach|mas)$', re.IGNORECASE),
                'split': lambda match: [match.group(1), match.group(2)],
                'description': 'fish compounds'
            },
            {
                'pattern': re.compile(r'(boro|choto|lal|nil|holud)(\w+)$', re.IGNORECASE),
                'split': lambda match: [match.group(1), match.group(2)],
                'description': 'adjective compounds'
            },
            {
                'pattern': re.compile(r'(\w+)(khana|gulo|ta|ti)$', re.IGNORECASE),
                'split': lambda match: [match.group(1), match.group(2)],
                'description': 'quantity compounds'
            }
        ]
        
        rule_types = [r['description'] for r in rules]
        logger.debug("Compound splitting rules built",
                    event_type="compound_rules_init",
                    total_rules=len(rules),
                    rule_categories=rule_types)
        return rules
    
    def _load_adaptive_cache(self) -> Dict:
        """Load adaptive cache with comprehensive logging"""
        try:
            if Path(FEEDBACK_DATA_PATH).exists():
                with open(FEEDBACK_DATA_PATH, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                    
                logger.info("Adaptive cache loaded from file",
                           event_type="adaptive_cache_load",
                           cache_file=FEEDBACK_DATA_PATH,
                           entries_loaded=len(cache),
                           file_exists=True,
                           status="success")
                return cache
                
        except json.JSONDecodeError as e:
            logger.error("Adaptive cache file corrupted",
                        event_type="adaptive_cache_load",
                        cache_file=FEEDBACK_DATA_PATH,
                        error=str(e),
                        error_type="json_decode_error",
                        status="corrupted_file")
        except Exception as e:
            logger.warning("Failed to load adaptive cache",
                          event_type="adaptive_cache_load",
                          cache_file=FEEDBACK_DATA_PATH,
                          error=str(e),
                          error_type=type(e).__name__,
                          status="load_failed")
        
        logger.info("Initialized empty adaptive cache",
                   event_type="adaptive_cache_load",
                   cache_file=FEEDBACK_DATA_PATH,
                   entries_loaded=0,
                   file_exists=False,
                   status="empty_init")
        return {}
    
    def _save_adaptive_cache(self):
        """Save adaptive cache with comprehensive logging"""
        try:
            with open(FEEDBACK_DATA_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.adaptive_cache, f, ensure_ascii=False, indent=2)
                
            logger.info("Adaptive cache saved successfully",
                       event_type="adaptive_cache_save",
                       cache_file=FEEDBACK_DATA_PATH,
                       entries_saved=len(self.adaptive_cache),
                       file_size_bytes=Path(FEEDBACK_DATA_PATH).stat().st_size if Path(FEEDBACK_DATA_PATH).exists() else 0,
                       status="success")
                       
        except PermissionError as e:
            logger.error("Permission denied saving adaptive cache",
                        event_type="adaptive_cache_save",
                        cache_file=FEEDBACK_DATA_PATH,
                        entries_attempted=len(self.adaptive_cache),
                        error=str(e),
                        error_type="permission_error",
                        status="permission_denied")
        except Exception as e:
            logger.error("Failed to save adaptive cache",
                        event_type="adaptive_cache_save",
                        cache_file=FEEDBACK_DATA_PATH,
                        entries_attempted=len(self.adaptive_cache),
                        error=str(e),
                        error_type=type(e).__name__,
                        status="save_failed")
    
    @log_execution_time(logger, "slang_normalization")
    def _normalize_slang(self, text: str) -> str:
        """Step 1: Normalize slang with logging"""
        words = text.split()
        normalized = []
        changes_made = 0
        
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word.lower())
            if clean_word in self.slang_map:
                normalized.append(self.slang_map[clean_word])
                changes_made += 1
            else:
                normalized.append(word)
        
        result = ' '.join(normalized)
        
        if changes_made > 0:
            logger.debug("Slang normalization applied", 
                        event_type="slang_normalization",
                        original_text=text[:100],  # Truncate for privacy
                        normalized_text=result[:100],
                        changes_made=changes_made,
                        total_words=len(words))
        
        return result
    
    def _phonetic_normalize(self, text: str) -> str:
        """Phonetic normalization with logging"""
        phonetic_map = {
            'ph': 'f', 'th': 't', 'ck': 'k', 'ch': 'c', 'sh': 's',
            'gh': 'g', 'kh': 'k', 'bh': 'b', 'dh': 'd', 'jh': 'j',
            'oo': 'u', 'ee': 'i'
        }
        
        original = text
        normalized = text.lower()
        changes = 0
        
        for old, new in phonetic_map.items():
            if old in normalized:
                normalized = normalized.replace(old, new)
                changes += 1
        
        if changes > 0:
            logger.debug("Phonetic normalization applied",
                        event_type="phonetic_normalization",
                        original_text=original[:100],
                        normalized_text=normalized[:100],
                        phonetic_changes=changes)
        
        return normalized
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate edit distance (optimized for logging)"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    @log_execution_time(logger, "fuzzy_matching")
    def _fuzzy_match(self, query: str, threshold: float = 0.8) -> Optional[Dict]:
        """Step 4: Fuzzy matching with detailed logging"""
        demo_phrases = [
            "kemon acho", "ami tomake bhalo bashi", "ki koro", 
            "dhonnobad", "bhalo achi", "ki khaba", "kothay jachcho"
        ]
        
        candidates = []
        
        for phrase in demo_phrases:
            distance = self._levenshtein_distance(query.lower(), phrase.lower())
            max_len = max(len(query), len(phrase))
            similarity = 1 - (distance / max_len) if max_len > 0 else 0
            
            if similarity >= threshold:
                translation_result = self.db_lookup(phrase, "banglish_to_english")
                if translation_result:
                    candidates.append({
                        'phrase': phrase,
                        'translation': translation_result['english'],
                        'similarity': similarity,
                        'distance': distance
                    })
        
        if candidates:
            best = max(candidates, key=lambda x: x['similarity'])
            
            logger.info("Fuzzy match found",
                       event_type="fuzzy_match_success",
                       query_length=len(query),
                       matched_phrase=best['phrase'],
                       similarity=round(best['similarity'], 3),
                       edit_distance=best['distance'],
                       candidates_evaluated=len(demo_phrases),
                       candidates_viable=len(candidates))
            
            return {
                'translation': best['translation'],
                'confidence': best['similarity'] * 0.9,
                'method': 'fuzzy',
                'original': best['phrase'],
                'similarity': best['similarity']
            }
        
        logger.debug("Fuzzy match failed", 
                    event_type="fuzzy_match_failed",
                    query_length=len(query),
                    threshold=threshold,
                    candidates_evaluated=len(demo_phrases),
                    viable_candidates=0)
        return None
    
    @log_execution_time(logger, "compound_word_splitting")
    def _compound_word_split(self, query: str) -> Optional[Dict]:
        """Step 5: Compound word splitting with logging"""
        for rule in self.compound_rules:
            match = rule['pattern'].match(query)
            if match:
                try:
                    parts = rule['split'](match)
                    translated_parts = []
                    confidence_sum = 0
                    translation_details = []
                    
                    for part in parts:
                        part_result = self.db_lookup(part, "banglish_to_english")
                        if part_result:
                            translated_parts.append(part_result['english'])
                            confidence_sum += 1.0
                            translation_details.append({
                                'part': part,
                                'translation': part_result['english'],
                                'found': True
                            })
                        else:
                            translated_parts.append(part)
                            confidence_sum += 0.3
                            translation_details.append({
                                'part': part,
                                'translation': part,
                                'found': False
                            })
                    
                    if translated_parts:
                        avg_confidence = confidence_sum / len(parts)
                        
                        logger.info("Compound word split successful",
                                   event_type="compound_split_success",
                                   query=query,
                                   rule_applied=rule['description'],
                                   parts_found=parts,
                                   translation_details=translation_details,
                                   confidence=round(avg_confidence, 3),
                                   parts_translated=len([d for d in translation_details if d['found']]))
                        
                        return {
                            'translation': ' '.join(translated_parts),
                            'confidence': min(avg_confidence * 0.85, 0.9),
                            'method': 'compound',
                            'split_parts': parts,
                            'description': rule['description']
                        }
                except Exception as e:
                    logger.warning("Compound rule processing failed",
                                  event_type="compound_split_error",
                                  query=query,
                                  rule_description=rule['description'],
                                  error=str(e),
                                  error_type=type(e).__name__)
                    continue
        
        logger.debug("Compound splitting failed",
                    event_type="compound_split_failed", 
                    query=query,
                    rules_attempted=len(self.compound_rules))
        return None
    
    @log_execution_time(logger, "pattern_matching")
    def _pattern_match(self, query: str) -> Optional[Dict]:
        """Step 6: Pattern matching with detailed logging"""
        for matcher in self.pattern_matchers:
            match = matcher['pattern'].match(query)
            if match:
                try:
                    base_part = match.group(1) if match.groups() else ""
                    
                    # Try to translate base part
                    base_translation = base_part
                    base_result = self.db_lookup(base_part, "banglish_to_english")
                    if base_result:
                        base_translation = base_result['english']
                    else:
                        base_translation = self._word_by_word_translate(base_part)
                    
                    # Apply pattern transformation
                    translation = matcher['transform'](match, base_translation)
                    
                    logger.info("Pattern match successful",
                               event_type="pattern_match_success",
                               query=query,
                               pattern_name=matcher['name'],
                               base_part=base_part,
                               base_translation=base_translation,
                               final_translation=translation,
                               confidence=matcher['confidence'])
                    
                    return {
                        'translation': translation,
                        'confidence': matcher['confidence'],
                        'method': 'pattern',
                        'pattern': matcher['name'],
                        'base_part': base_part
                    }
                except Exception as e:
                    logger.warning("Pattern transformation failed",
                                  event_type="pattern_match_error",
                                  query=query,
                                  pattern_name=matcher['name'],
                                  error=str(e),
                                  error_type=type(e).__name__)
                    continue
        
        logger.debug("Pattern matching failed", 
                    event_type="pattern_match_failed",
                    query=query,
                    patterns_attempted=len(self.pattern_matchers))
        return None
    
    def _word_by_word_translate(self, query: str) -> str:
        """Basic word-by-word translation with logging"""
        words = query.split()
        translated = []
        found_count = 0
        
        for word in words:
            result = self.db_lookup(word, "banglish_to_english")
            if result:
                translated.append(result['english'])
                found_count += 1
            else:
                translated.append(word)
        
        if found_count > 0:
            logger.debug("Word-by-word translation applied", 
                        event_type="word_by_word_basic",
                        query=query[:100],
                        words_found=found_count,
                        total_words=len(words),
                        success_rate=round(found_count/len(words), 2))
        
        return ' '.join(translated)
    
    @log_execution_time(logger, "weighted_word_by_word")
    def _weighted_word_by_word(self, query: str) -> Optional[Dict]:
        """Step 7: Weighted word-by-word with logging"""
        words = query.split()
        if not words:
            return None
            
        translated = []
        translated_count = 0
        word_details = []
        
        for word in words:
            result = self.db_lookup(word, "banglish_to_english")
            if result:
                translated.append(result['english'])
                translated_count += 1
                word_details.append({'word': word, 'translation': result['english'], 'found': True})
            else:
                translated.append(word)
                word_details.append({'word': word, 'translation': word, 'found': False})
        
        if translated_count > 0:
            confidence = translated_count / len(words)
            
            logger.info("Weighted word-by-word translation",
                       event_type="weighted_word_by_word_success",
                       query=query[:100],
                       word_details=word_details,
                       translated_count=translated_count,
                       total_words=len(words),
                       confidence=round(confidence, 3))
            
            return {
                'translation': ' '.join(translated),
                'confidence': min(confidence * 0.7, 0.85),
                'method': 'word_by_word',
                'translated_words': translated_count,
                'total_words': len(words)
            }
        
        logger.debug("Word-by-word translation failed", 
                    event_type="weighted_word_by_word_failed",
                    query=query[:100],
                    total_words=len(words))
        return None
    
    @log_execution_time(logger, "full_translation")
    def translate(self, query: str, direction: str = "banglish_to_english") -> Optional[Dict]:
        """
        Main translation method with comprehensive step-by-step logging
        """
        if not query or not query.strip():
            logger.warning("Empty query received for translation",
                          event_type="translation_request_invalid",
                          reason="empty_query")
            return None
        
        query = query.strip()
        translation_start_time = time.time()
        
        # Log the translation request
        logger.translation_request(query, direction)
        
        # Step 1: Check adaptive cache
        cache_key = f"{query}:{direction}"
        if cache_key in self.adaptive_cache:
            result = self.adaptive_cache[cache_key].copy()
            result['method'] = 'adaptive_cache'
            
            processing_time = (time.time() - translation_start_time) * 1000
            logger.translation_result(query, {'success': True, 'method': 'adaptive_cache', 'confidence': result.get('confidence', 0.9)}, processing_time)
            
            return result
        
        # Step 2: Normalize slang
        normalized_query = self._normalize_slang(query)
        
        # Step 3: Exact match
        exact_result = self.db_lookup(normalized_query, direction)
        if exact_result:
            if direction == "banglish_to_english":
                result = {
                    'translation': exact_result['english'],
                    'confidence': 1.0,
                    'method': 'exact'
                }
            else:
                result = {
                    'translation': exact_result.get('banglish', exact_result.get('english', '')),
                    'confidence': 1.0,
                    'method': 'exact'
                }
            
            processing_time = (time.time() - translation_start_time) * 1000
            logger.translation_result(query, {'success': True, 'method': 'exact', 'confidence': 1.0}, processing_time)
            
            return result
        
        # Try phonetic normalization
        phonetic_query = self._phonetic_normalize(normalized_query)
        if phonetic_query != normalized_query:
            phonetic_result = self.db_lookup(phonetic_query, direction)
            if phonetic_result:
                result = {
                    'translation': phonetic_result['english'],
                    'confidence': 0.95,
                    'method': 'phonetic',
                    'phonetic_form': phonetic_query
                }
                
                processing_time = (time.time() - translation_start_time) * 1000
                logger.translation_result(query, {'success': True, 'method': 'phonetic', 'confidence': 0.95}, processing_time)
                
                return result
        
        # Only proceed with advanced methods for banglish_to_english
        if direction != "banglish_to_english":
            processing_time = (time.time() - translation_start_time) * 1000
            logger.translation_result(query, {'success': False, 'method': 'none', 'confidence': 0}, processing_time)
            return None
        
        # Step 4: Fuzzy matching
        fuzzy_result = self._fuzzy_match(normalized_query)
        if fuzzy_result:
            processing_time = (time.time() - translation_start_time) * 1000
            logger.translation_result(query, {'success': True, 'method': 'fuzzy', 'confidence': fuzzy_result['confidence']}, processing_time)
            return fuzzy_result
        
        # Step 5: Compound word splitting
        compound_result = self._compound_word_split(normalized_query)
        if compound_result:
            processing_time = (time.time() - translation_start_time) * 1000
            logger.translation_result(query, {'success': True, 'method': 'compound', 'confidence': compound_result['confidence']}, processing_time)
            return compound_result
        
        # Step 6: Pattern matching
        pattern_result = self._pattern_match(normalized_query)
        if pattern_result:
            processing_time = (time.time() - translation_start_time) * 1000
            logger.translation_result(query, {'success': True, 'method': 'pattern', 'confidence': pattern_result['confidence']}, processing_time)
            return pattern_result
        
        # Step 7: Weighted word-by-word fallback
        word_result = self._weighted_word_by_word(normalized_query)
        if word_result:
            processing_time = (time.time() - translation_start_time) * 1000
            logger.translation_result(query, {'success': True, 'method': 'word_by_word', 'confidence': word_result['confidence']}, processing_time)
            return word_result
        
        # No translation found
        processing_time = (time.time() - translation_start_time) * 1000
        logger.translation_result(query, {'success': False, 'method': 'none', 'confidence': 0}, processing_time)
        logger.translation_miss(query, direction)
        
        return None
    
    def add_feedback(self, query: str, direction: str, suggested_translation: str, is_correct: bool):
        """Add user feedback with comprehensive logging"""
        cache_key = f"{query}:{direction}"
        
        if is_correct:
            self.adaptive_cache[cache_key] = {
                'translation': suggested_translation,
                'confidence': 0.9,
                'method': 'user_feedback',
                'feedback_count': self.adaptive_cache.get(cache_key, {}).get('feedback_count', 0) + 1
            }
            self._save_adaptive_cache()
            
            logger.user_feedback(query, "positive_correction", True)
            logger.info("Positive user feedback recorded",
                       event_type="user_feedback_positive",
                       query_length=len(query),
                       direction=direction,
                       suggested_translation_length=len(suggested_translation),
                       cache_size=len(self.adaptive_cache),
                       learning_impact="high")
            
        else:
            self.adaptive_cache.pop(cache_key, None)
            self._save_adaptive_cache()
            
            logger.user_feedback(query, "negative_feedback", False)
            logger.info("Negative user feedback recorded",
                       event_type="user_feedback_negative",
                       query_length=len(query),
                       direction=direction,
                       cache_size=len(self.adaptive_cache),
                       learning_impact="corrective")


# Global translator engine instance
_engine = EnhancedTranslationEngine()

def set_db_lookup_function(db_lookup_func):
    """Wire DB into engine from external context (main.py)"""
    _engine.db_lookup = db_lookup_func

# Export router to main.py and engine instance
translator_engine = _engine