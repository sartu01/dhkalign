"""
DatabaseManager - Enhanced with structured logging integration
Upgraded from print() statements to comprehensive structured logging with metadata.
"""

import sqlite3
import pandas as pd
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

# Import enhanced logging system
from logger import logger, log_execution_time

class DatabaseManager:
    """
    Database manager with comprehensive structured logging
    All operations now flow into structured log files with searchable metadata
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db_directory()
        self.init_database()
        
        logger.info("DatabaseManager initialized", 
                   event_type="db_manager_init",
                   db_path=self.db_path,
                   status="ready")
    
    def _ensure_db_directory(self):
        """Create database directory with structured logging"""
        db_dir = Path(self.db_path).parent
        if not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Database directory created", 
                       event_type="db_init",
                       directory=str(db_dir),
                       action="directory_created")
        else:
            logger.debug("Database directory exists", 
                        event_type="db_init",
                        directory=str(db_dir),
                        action="directory_verified")
    
    @log_execution_time(logger, "database_connection")
    def get_connection(self) -> sqlite3.Connection:
        """Get optimized SQLite connection with logging"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            
            # SQLite optimizations
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL") 
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            
            logger.debug("Database connection established",
                        event_type="db_connection",
                        journal_mode="WAL",
                        cache_size="10000",
                        status="optimized")
            
            return conn
            
        except sqlite3.Error as e:
            logger.error("Database connection failed",
                        event_type="db_connection",
                        error=str(e),
                        db_path=self.db_path,
                        status="failed")
            raise
    
    @log_execution_time(logger, "database_schema_init")
    def init_database(self) -> None:
        """Initialize database schema with comprehensive logging"""
        start_time = time.time()
        tables_created = []
        indexes_created = []
        
        try:
            with self.get_connection() as conn:
                # Main translations table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS translations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        banglish TEXT NOT NULL,
                        english TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                tables_created.append("translations")
                
                # Performance indexes
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_banglish 
                    ON translations(banglish COLLATE NOCASE)
                """)
                indexes_created.append("idx_banglish")
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_english 
                    ON translations(english COLLATE NOCASE)
                """)
                indexes_created.append("idx_english")
                
                # Missed queries for learning
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS missed_queries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query TEXT NOT NULL,
                        direction TEXT NOT NULL CHECK (direction IN ('banglish_to_english', 'english_to_banglish')),
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        session_id TEXT
                    )
                """)
                tables_created.append("missed_queries")
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_missed_timestamp 
                    ON missed_queries(timestamp DESC)
                """)
                indexes_created.append("idx_missed_timestamp")
                
                conn.commit()
                
                duration_ms = (time.time() - start_time) * 1000
                
                logger.info("Database schema initialized",
                           event_type="db_schema",
                           status="complete",
                           tables_created=tables_created,
                           indexes_created=indexes_created,
                           duration_ms=round(duration_ms, 2),
                           total_objects=len(tables_created) + len(indexes_created))
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("Database schema initialization failed",
                        event_type="db_schema",
                        status="failed",
                        error=str(e),
                        duration_ms=round(duration_ms, 2),
                        tables_attempted=len(tables_created),
                        error_type=type(e).__name__)
            raise
    
    @log_execution_time(logger, "translation_lookup")
    def find_translation(self, query: str, direction: str) -> Optional[Dict[str, str]]:
        """
        Find translation with detailed performance logging
        
        Returns:
            For banglish_to_english: {'english': 'translation'} or None
            For english_to_banglish: {'banglish': 'translation'} or None
        """
        start_time = time.time()
        query_lower = query.lower()
        
        try:
            with self.get_connection() as conn:
                if direction == "banglish_to_english":
                    cursor = conn.execute(
                        "SELECT english FROM translations WHERE banglish = ? COLLATE NOCASE",
                        (query_lower,)
                    )
                    row = cursor.fetchone()
                    duration_ms = (time.time() - start_time) * 1000
                    
                    if row:
                        logger.info("Translation lookup successful",
                                   event_type="translation_lookup",
                                   direction=direction,
                                   query_length=len(query),
                                   result_found=True,
                                   duration_ms=round(duration_ms, 2),
                                   cache_status="hit")
                        return {"english": row[0]}
                    else:
                        logger.debug("Translation lookup miss",
                                    event_type="translation_lookup",
                                    direction=direction,
                                    query_length=len(query),
                                    result_found=False,
                                    duration_ms=round(duration_ms, 2),
                                    cache_status="miss")
                        return None
                
                elif direction == "english_to_banglish":
                    cursor = conn.execute(
                        "SELECT banglish FROM translations WHERE english = ? COLLATE NOCASE", 
                        (query_lower,)
                    )
                    row = cursor.fetchone()
                    duration_ms = (time.time() - start_time) * 1000
                    
                    if row:
                        logger.info("Reverse translation lookup successful",
                                   event_type="translation_lookup",
                                   direction=direction,
                                   query_length=len(query),
                                   result_found=True,
                                   duration_ms=round(duration_ms, 2))
                        return {"banglish": row[0]}
                    else:
                        logger.debug("Reverse translation lookup miss",
                                    event_type="translation_lookup",
                                    direction=direction,
                                    query_length=len(query),
                                    result_found=False,
                                    duration_ms=round(duration_ms, 2))
                        return None
                
                logger.warning("Invalid translation direction",
                              event_type="translation_lookup",
                              direction=direction,
                              valid_directions=["banglish_to_english", "english_to_banglish"],
                              status="invalid_direction")
                return None
                
        except sqlite3.Error as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("Translation lookup database error",
                        event_type="translation_lookup",
                        direction=direction,
                        query_length=len(query),
                        error=str(e),
                        duration_ms=round(duration_ms, 2),
                        error_type="sqlite_error")
            return None
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("Translation lookup unexpected error",
                        event_type="translation_lookup",
                        direction=direction,
                        query_length=len(query),
                        error=str(e),
                        duration_ms=round(duration_ms, 2),
                        error_type=type(e).__name__)
            return None
    
    @log_execution_time(logger, "csv_data_loading")
    def load_csv_data(self, csv_path: str) -> int:
        """
        Load translation pairs from CSV with comprehensive progress logging
        """
        csv_file = Path(csv_path)
        if not csv_file.exists():
            logger.warning("CSV file not found",
                          event_type="csv_load",
                          csv_path=csv_path,
                          status="file_not_found")
            return 0
        
        start_time = time.time()
        
        try:
            # File size and initial validation
            file_size_mb = round(csv_file.stat().st_size / (1024 * 1024), 2)
            logger.info("CSV load initiated",
                       event_type="csv_load",
                       csv_path=csv_path,
                       file_size_mb=file_size_mb,
                       status="started")
            
            # Read CSV with pandas
            df = pd.read_csv(csv_path, encoding='utf-8', na_filter=False)
            
            # Validate required columns
            required_columns = ['banglish', 'english']
            available_columns = list(df.columns)
            missing_columns = [col for col in required_columns if col not in available_columns]
            
            if missing_columns:
                logger.error("CSV schema validation failed",
                            event_type="csv_load",
                            csv_path=csv_path,
                            required_columns=required_columns,
                            available_columns=available_columns,
                            missing_columns=missing_columns,
                            status="schema_invalid")
                return 0
            
            # Data cleaning pipeline with metrics
            original_count = len(df)
            logger.info("CSV data cleaning started",
                       event_type="csv_load",
                       original_rows=original_count,
                       status="cleaning_started")
            
            # Remove null values
            df_before_null = len(df)
            df = df.dropna(subset=['banglish', 'english'])
            null_removed = df_before_null - len(df)
            
            # Clean and normalize data
            df['banglish'] = df['banglish'].astype(str).str.strip().str.lower()
            df['english'] = df['english'].astype(str).str.strip()
            
            # Remove empty entries
            df_before_empty = len(df)
            df = df[(df['banglish'] != '') & (df['english'] != '')]
            empty_removed = df_before_empty - len(df)
            
            # Remove duplicates
            df_before_dupes = len(df)
            df = df.drop_duplicates(subset=['banglish', 'english'])
            dupes_removed = df_before_dupes - len(df)
            
            cleaned_count = len(df)
            data_quality_percent = round((cleaned_count / original_count) * 100, 1) if original_count > 0 else 0
            
            logger.info("CSV data cleaning completed",
                       event_type="csv_load",
                       original_rows=original_count,
                       cleaned_rows=cleaned_count,
                       null_rows_removed=null_removed,
                       empty_rows_removed=empty_removed,
                       duplicate_rows_removed=dupes_removed,
                       data_quality_percent=data_quality_percent,
                       status="cleaning_complete")
            
            # Load into database (replace existing data)
            with self.get_connection() as conn:
                # Clear existing data
                conn.execute("DELETE FROM translations")
                rows_deleted = conn.rowcount
                
                # Bulk insert for performance
                df.to_sql('translations', conn, if_exists='append', index=False)
                conn.commit()
                
                # Verify the load
                actual_count = conn.execute("SELECT COUNT(*) FROM translations").fetchone()[0]
                
                duration_ms = (time.time() - start_time) * 1000
                
                logger.info("CSV load completed successfully",
                           event_type="csv_load",
                           csv_path=csv_path,
                           file_size_mb=file_size_mb,
                           original_rows=original_count,
                           cleaned_rows=cleaned_count,
                           loaded_rows=actual_count,
                           rows_deleted=rows_deleted,
                           data_quality_percent=data_quality_percent,
                           duration_ms=round(duration_ms, 2),
                           load_rate_rows_per_second=round(actual_count / (duration_ms / 1000), 0) if duration_ms > 0 else 0,
                           status="success")
                
                return actual_count
                
        except pd.errors.EmptyDataError:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("CSV file is empty",
                        event_type="csv_load",
                        csv_path=csv_path,
                        duration_ms=round(duration_ms, 2),
                        error_type="empty_file",
                        status="failed")
            return 0
        except pd.errors.ParserError as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("CSV parsing failed",
                        event_type="csv_load",
                        csv_path=csv_path,
                        error=str(e),
                        duration_ms=round(duration_ms, 2),
                        error_type="parse_error",
                        status="failed")
            return 0
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("CSV load failed with unexpected error",
                        event_type="csv_load",
                        csv_path=csv_path,
                        error=str(e),
                        duration_ms=round(duration_ms, 2),
                        error_type=type(e).__name__,
                        status="failed")
            return 0
    
    def log_missed_query(self, query: str, direction: str, session_id: str = None):
        """Log translation requests that couldn't be fulfilled"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO missed_queries (query, direction, session_id)
                    VALUES (?, ?, ?)
                """, (query, direction, session_id))
                conn.commit()
                
                logger.info("Missed query logged",
                           event_type="missed_query",
                           query_length=len(query),
                           direction=direction,
                           session_id=session_id[:8] + "..." if session_id else None,
                           priority="dataset_expansion",
                           status="logged")
                
        except Exception as e:
            logger.error("Failed to log missed query",
                        event_type="missed_query",
                        query_length=len(query) if query else 0,
                        direction=direction,
                        error=str(e),
                        error_type=type(e).__name__,
                        status="failed")
    
    @log_execution_time(logger, "database_stats_query")
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics with performance logging"""
        start_time = time.time()
        
        try:
            with self.get_connection() as conn:
                stats = {}
                
                # Core counts
                stats['translation_pairs'] = conn.execute("SELECT COUNT(*) FROM translations").fetchone()[0]
                stats['missed_queries'] = conn.execute("SELECT COUNT(*) FROM missed_queries").fetchone()[0]
                
                # Recent activity metrics
                stats['missed_queries_24h'] = conn.execute("""
                    SELECT COUNT(*) FROM missed_queries 
                    WHERE timestamp > datetime('now', '-24 hours')
                """).fetchone()[0]
                
                stats['missed_queries_7d'] = conn.execute("""
                    SELECT COUNT(*) FROM missed_queries 
                    WHERE timestamp > datetime('now', '-7 days')
                """).fetchone()[0]
                
                # Top missed queries for dataset expansion
                top_missed_cursor = conn.execute("""
                    SELECT query, direction, COUNT(*) as frequency
                    FROM missed_queries 
                    WHERE timestamp > datetime('now', '-7 days')
                    GROUP BY query, direction
                    ORDER BY frequency DESC
                    LIMIT 5
                """)
                stats['top_missed_queries'] = [dict(row) for row in top_missed_cursor.fetchall()]
                
                # Database file metrics
                db_size_bytes = 0
                db_size_mb = 0
                if Path(self.db_path).exists():
                    db_size_bytes = Path(self.db_path).stat().st_size
                    db_size_mb = round(db_size_bytes / (1024 * 1024), 2)
                
                stats['database'] = {
                    "size_mb": db_size_mb,
                    "size_bytes": db_size_bytes,
                    "path": str(self.db_path),
                    "status": "healthy"
                }
                
                # Activity analysis
                activity_level = "low"
                if stats['missed_queries_24h'] > 100:
                    activity_level = "high"
                elif stats['missed_queries_24h'] > 10:
                    activity_level = "medium"
                
                stats['activity_analysis'] = {
                    "level": activity_level,
                    "recent_activity_score": stats['missed_queries_24h'],
                    "growth_trend": "increasing" if stats['missed_queries_24h'] > stats['missed_queries_7d'] / 7 else "stable"
                }
                
                duration_ms = (time.time() - start_time) * 1000
                
                logger.info("Database statistics generated",
                           event_type="db_stats",
                           translation_pairs=stats['translation_pairs'],
                           missed_queries_total=stats['missed_queries'],
                           missed_queries_24h=stats['missed_queries_24h'],
                           database_size_mb=db_size_mb,
                           activity_level=activity_level,
                           duration_ms=round(duration_ms, 2),
                           status="success")
                
                return stats
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("Database statistics generation failed",
                        event_type="db_stats",
                        error=str(e),
                        duration_ms=round(duration_ms, 2),
                        error_type=type(e).__name__,
                        status="failed")
            return {
                "error": str(e),
                "status": "error",
                "timestamp": time.time()
            }
    
    @log_execution_time(logger, "admin_add_translation")
    def add_translation(self, banglish: str, english: str) -> bool:
        """Add a new translation pair with logging (admin function)"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO translations (banglish, english)
                    VALUES (?, ?)
                """, (banglish.lower().strip(), english.strip()))
                conn.commit()
                
                logger.info("Translation pair added",
                           event_type="admin_add",
                           banglish_length=len(banglish),
                           english_length=len(english),
                           action="insert_or_replace",
                           status="success")
                
                return True
                
        except Exception as e:
            logger.error("Failed to add translation pair",
                        event_type="admin_add",
                        banglish_length=len(banglish) if banglish else 0,
                        english_length=len(english) if english else 0,
                        error=str(e),
                        error_type=type(e).__name__,
                        status="failed")
            return False
    
    @log_execution_time(logger, "search_translations")
    def search_translations(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for translations containing the query with logging"""
        start_time = time.time()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT banglish, english FROM translations 
                    WHERE banglish LIKE ? OR english LIKE ?
                    ORDER BY banglish
                    LIMIT ?
                """, (f"%{query}%", f"%{query}%", limit))
                
                results = [{"banglish": row[0], "english": row[1]} for row in cursor.fetchall()]
                
                duration_ms = (time.time() - start_time) * 1000
                
                logger.info("Translation search completed",
                           event_type="search_query",
                           query=query,
                           query_length=len(query),
                           results_found=len(results),
                           search_limit=limit,
                           duration_ms=round(duration_ms, 2),
                           status="success")
                
                return results
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("Translation search failed",
                        event_type="search_query",
                        query=query,
                        query_length=len(query),
                        search_limit=limit,
                        error=str(e),
                        duration_ms=round(duration_ms, 2),
                        error_type=type(e).__name__,
                        status="failed")
            return []
    
    @log_execution_time(logger, "sample_data_creation")
    def create_sample_data(self) -> int:
        """Create sample translation data with comprehensive logging"""
        sample_translations = [
            ("kemon acho", "how are you"),
            ("ami tomake bhalo bashi", "I love you"),
            ("ki koro", "what are you doing"),
            ("dhonnobad", "thank you"),
            ("ki khaba", "what will you eat"),
            ("kothay jachcho", "where are you going"),
            ("bhalo achi", "I am fine"),
            ("amar nam", "my name is"),
            ("tomar nam ki", "what is your name"),
            ("choto mach", "small fish"),
            ("boro bari", "big house"),
            ("tumi", "you"),
            ("ami", "I"),
            ("bari", "home"),
            ("mach", "fish"),
            ("boro", "big"),
            ("choto", "small"),
            ("lal", "red"),
            ("nil", "blue"),
            ("holud", "yellow"),
            ("khela", "play"),
            ("koro", "do"),
            ("korbo", "will do"),
            ("korbe", "will do"),
            ("ache", "have"),
            ("ase", "comes")
        ]
        
        start_time = time.time()
        
        try:
            with self.get_connection() as conn:
                conn.executemany("""
                    INSERT OR REPLACE INTO translations (banglish, english)
                    VALUES (?, ?)
                """, sample_translations)
                conn.commit()
                
                count = len(sample_translations)
                duration_ms = (time.time() - start_time) * 1000
                
                logger.info("Sample data created successfully",
                           event_type="sample_data",
                           sample_entries=count,
                           categories=["greetings", "questions", "objects", "colors", "actions"],
                           duration_ms=round(duration_ms, 2),
                           insertion_rate=round(count / (duration_ms / 1000), 0) if duration_ms > 0 else 0,
                           status="success")
                
                return count
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("Sample data creation failed",
                        event_type="sample_data",
                        attempted_entries=len(sample_translations),
                        error=str(e),
                        duration_ms=round(duration_ms, 2),
                        error_type=type(e).__name__,
                        status="failed")
            return 0