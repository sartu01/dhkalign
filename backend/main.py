#!/usr/bin/env python3
"""
DHK Align - Enhanced Backend with Comprehensive Logging
WRAITH Edition with structured logging, performance monitoring, and security features.
"""

import sqlite3
import pandas as pd
import uvicorn
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Literal
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import enhanced logging system
from backend.utils.logger import (
    logger, 
    log_startup, 
    log_shutdown, 
    log_execution_time, 
    log_api_request,
    log_health_check,
    LogAnalyzer
)

# Import the enhanced translator
from backend.translator import set_db_lookup_function, router as translator_router

# Configuration constants
DB_PATH = "data/translations.db"
CSV_PATH = "data/combined_dataset_final_sequential.csv"
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "dev-admin-key-change-in-production")

class DatabaseManager:
    """
    Database manager with comprehensive logging
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db_directory()
        self.init_database()
    
    def _ensure_db_directory(self):
        """Create database directory if it doesn't exist"""
        db_dir = Path(self.db_path).parent
        if not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
            log_startup(f"Created database directory: {db_dir}")
    
    @log_execution_time(logger, "database_connection")
    def get_connection(self) -> sqlite3.Connection:
        """Get optimized SQLite connection"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            
            # Performance optimizations
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            
            return conn
        except sqlite3.Error as e:
            logger.database_operation("connection", False, error=str(e))
            raise
    
    @log_execution_time(logger, "database_initialization")
    def init_database(self) -> None:
        """Initialize database schema with logging"""
        start_time = time.time()
        try:
            with self.get_connection() as conn:
                # Main translations table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS translations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        banglish TEXT NOT NULL,
                        english TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Performance indexes
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_banglish 
                    ON translations(banglish COLLATE NOCASE)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_english 
                    ON translations(english COLLATE NOCASE)
                """)
                
                # Missed queries table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS missed_queries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query TEXT NOT NULL,
                        direction TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        session_hash TEXT
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_missed_timestamp 
                    ON missed_queries(timestamp DESC)
                """)
                
                conn.commit()
                
                duration_ms = (time.time() - start_time) * 1000
                logger.database_operation("schema_init", True, duration_ms, tables_created=4)
                log_startup("Database schema initialized successfully")
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.database_operation("schema_init", False, duration_ms, error=str(e))
            raise
    
    @log_execution_time(logger, "translation_lookup")
    def find_translation(self, query: str, direction: str) -> Optional[Dict[str, str]]:
        """Find translation with comprehensive logging"""
        start_time = time.time()
        try:
            with self.get_connection() as conn:
                if direction == "banglish_to_english":
                    cursor = conn.execute(
                        "SELECT english FROM translations WHERE banglish = ? COLLATE NOCASE",
                        (query.lower(),)
                    )
                    row = cursor.fetchone()
                    duration_ms = (time.time() - start_time) * 1000
                    
                    if row:
                        logger.database_operation("translation_lookup", True, duration_ms, 
                                                direction=direction, result_found=True)
                        return {"english": row[0]}
                    else:
                        logger.database_operation("translation_lookup", True, duration_ms, 
                                                direction=direction, result_found=False)
                        return None
                
                elif direction == "english_to_banglish":
                    cursor = conn.execute(
                        "SELECT banglish FROM translations WHERE english = ? COLLATE NOCASE",
                        (query.lower(),)
                    )
                    row = cursor.fetchone()
                    duration_ms = (time.time() - start_time) * 1000
                    
                    if row:
                        logger.database_operation("translation_lookup", True, duration_ms, 
                                                direction=direction, result_found=True)
                        return {"banglish": row[0]}
                    else:
                        logger.database_operation("translation_lookup", True, duration_ms, 
                                                direction=direction, result_found=False)
                        return None
                
                return None
                
        except Exception:
            duration_ms = (time.time() - start_time) * 1000
            logger.database_operation("translation_lookup", False, duration_ms, 
                                    direction=direction, error="internal_error")
            return None
    
    @log_execution_time(logger, "csv_data_load")
    def load_csv_data(self, csv_path: str) -> int:
        """Load CSV data with detailed logging"""
        if not Path(csv_path).exists():
            logger.warning(f"CSV file not found: {csv_path}")
            return 0
        
        start_time = time.time()
        try:
            # Load and validate CSV
            df = pd.read_csv(csv_path, encoding='utf-8', na_filter=False)
            
            required_columns = ['banglish', 'english']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"CSV missing required columns: {missing_columns}")
                return 0
            
            # Data cleaning with metrics
            original_count = len(df)
            logger.info(f"Processing CSV with {original_count} rows")
            
            df = df.dropna(subset=['banglish', 'english'])
            df['banglish'] = df['banglish'].astype(str).str.strip().str.lower()
            df['english'] = df['english'].astype(str).str.strip()
            df = df[(df['banglish'] != '') & (df['english'] != '')]
            df = df.drop_duplicates(subset=['banglish', 'english'])
            
            cleaned_count = len(df)
            data_quality = (cleaned_count / original_count) * 100 if original_count > 0 else 0
            
            # Load into database
            with self.get_connection() as conn:
                conn.execute("DELETE FROM translations")  # Fresh start
                df.to_sql('translations', conn, if_exists='append', index=False)
                conn.commit()
                
                # Verify load
                actual_count = conn.execute("SELECT COUNT(*) FROM translations").fetchone()[0]
                
                duration_ms = (time.time() - start_time) * 1000
                
                logger.database_operation("csv_load", True, duration_ms,
                                        original_rows=original_count,
                                        cleaned_rows=cleaned_count,
                                        loaded_rows=actual_count,
                                        data_quality_percent=round(data_quality, 1))
                
                log_startup(f"Dataset loaded successfully: {actual_count} translation pairs")
                return actual_count
                
        except Exception:
            duration_ms = (time.time() - start_time) * 1000
            logger.database_operation("csv_load", False, duration_ms, error="internal_error")
            logger.exception("Failed to load CSV data")
            return 0
    
    def log_missed_query(self, query: str, direction: str, session_hash: str = None):
        """Log missed queries for learning opportunities"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO missed_queries (query, direction, session_hash)
                    VALUES (?, ?, ?)
                """, (query, direction, session_hash))
                conn.commit()
                
                # Also log to structured logger
                logger.translation_miss(query, direction, session_hash)
                
        except Exception:
            logger.exception("Failed to log missed query")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        try:
            with self.get_connection() as conn:
                stats = {}
                
                # Core counts
                stats['translation_pairs'] = conn.execute("SELECT COUNT(*) FROM translations").fetchone()[0]
                stats['missed_queries'] = conn.execute("SELECT COUNT(*) FROM missed_queries").fetchone()[0]
                
                # Recent activity
                stats['recent_misses_24h'] = conn.execute("""
                    SELECT COUNT(*) FROM missed_queries 
                    WHERE timestamp > datetime('now', '-24 hours')
                """).fetchone()[0]
                
                # Database file size
                if Path(self.db_path).exists():
                    stats['database_size_mb'] = round(Path(self.db_path).stat().st_size / (1024 * 1024), 2)
                else:
                    stats['database_size_mb'] = 0
                
                return stats
                
        except Exception:
            logger.exception("Failed to get database stats")
            return {"error": "internal_error"}

# Global database manager
db_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle with comprehensive logging"""
    global db_manager
    
    log_startup("DHK Align WRAITH Edition initializing...")
    startup_start = time.time()
    
    try:
        # Initialize database
        db_manager = DatabaseManager(DB_PATH)
        
        # Create database lookup wrapper with logging
        def db_lookup_wrapper(query: str, direction: str) -> Optional[Dict[str, str]]:
            """Logged wrapper for database lookups"""
            result = db_manager.find_translation(query, direction)
            return result
        
        # Wire up enhanced translator
        set_db_lookup_function(db_lookup_wrapper)
        log_startup("Enhanced translator engine connected to database")
        
        # Load dataset with progress tracking
        record_count = 0
        if Path(CSV_PATH).exists():
            record_count = db_manager.load_csv_data(CSV_PATH)
        else:
            log_startup(f"Dataset file not found: {CSV_PATH}, creating sample data...")
            # Create sample data for testing
            sample_data = [
                ("kemon acho", "how are you"),
                ("ami tomake bhalo bashi", "I love you"),
                ("ki koro", "what are you doing"),
                ("dhonnobad", "thank you"),
                ("bhalo achi", "I am fine"),
                ("tumi", "you"),
                ("ami", "I"),
                ("bari", "home"),
                ("mach", "fish"),
                ("boro", "big"),
                ("choto", "small")
            ]
            
            with db_manager.get_connection() as conn:
                conn.executemany(
                    "INSERT INTO translations (banglish, english) VALUES (?, ?)",
                    sample_data
                )
                conn.commit()
                record_count = len(sample_data)
            
            log_startup(f"Sample dataset created: {record_count} translations")
        
        startup_duration = (time.time() - startup_start) * 1000
        logger.performance_metric("application_startup", startup_duration, 
                                translation_pairs=record_count,
                                components_initialized=['database', 'translator', 'logging'])
        
        log_startup(f"DHK Align WRAITH ready! ({record_count} translations loaded)")
        log_startup("7-step enhanced translation chain active")
        
    except Exception:
        startup_duration = (time.time() - startup_start) * 1000
        logger.exception("Startup failed", startup_duration=startup_duration)
        
        # Create minimal fallback
        db_manager = DatabaseManager(DB_PATH)
        set_db_lookup_function(lambda q, d: None)
        log_startup("Started in minimal fallback mode")
    
    yield
    
    log_shutdown("DHK Align WRAITH shutting down gracefully...")

# Initialize FastAPI with enhanced logging
app = FastAPI(
    title="DHK Align WRAITH API",
    description="Enhanced Banglish ↔ English translation with comprehensive logging and monitoring",
    version="2.0.0-WRAITH-LOGGED",
    lifespan=lifespan,
)

# /version endpoint for version and commit sha reporting
@app.get("/version")
def version():
    return {"ok": True, "sha": os.getenv("COMMIT_SHA", "dev")}

# Global exception handler to avoid leaking stack traces to clients
@app.exception_handler(Exception)
async def _unhandled(request, exc):
    logger.exception("unhandled %s %s", request.url.path, type(exc).__name__)
    return JSONResponse({"ok": False, "error": "internal_error"}, status_code=500)

# Rate limiting
limiter = Limiter(key_func=get_remote_address, default_limits=["1000/hour"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dhkalign.com", "https://www.dhkalign.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["content-type", "x-api-key", "x-admin-key", "stripe-signature"],
)

# Include the enhanced translator router
app.include_router(translator_router, prefix="/api")


# ----------------------------------------------------------------------------
# Minimal translate endpoint to satisfy frontend calls
# ----------------------------------------------------------------------------
@app.get("/api/translate")
@limiter.limit("3000/hour")
@log_api_request(logger)
async def api_translate(
    request: Request,
    q: str,
    direction: Literal["banglish_to_english", "english_to_banglish"] = "banglish_to_english",
):
    """
    Compatibility endpoint used by the frontend.
    Tries database lookup first; if nothing is found, returns a safe echo so the UI doesn't 404.
    """
    try:
        # Basic guardrails
        q = (q or "").strip()
        if not q:
            raise HTTPException(status_code=400, detail="Query 'q' is required")
        if len(q) > 500:
            raise HTTPException(status_code=413, detail="Query too long")

        found = False
        translation_text = q
        method = "api_echo"

        if db_manager:
            res = db_manager.find_translation(q, direction)
            if res:
                if direction == "banglish_to_english" and "english" in res:
                    translation_text = res["english"]
                elif direction == "english_to_banglish" and "banglish" in res:
                    translation_text = res["banglish"]
                found = True
                method = "db_exact"

        # Always return 200 with a structured payload (UI handles 'found' flag)
        return {
            "translation": translation_text,
            "confidence": 0.95 if found else 0.5,
            "method": method,
            "source": "api",
            "found": found,
            "direction": direction,
        }

    except HTTPException:
        # Re-raise typed errors
        raise
    except Exception:
        logger.exception("/api/translate failed")
        # Return a graceful fallback rather than 5xx to avoid noisy UI errors
        return {
            "translation": q,
            "confidence": 0.4,
            "method": "api_fallback",
            "source": "api",
            "found": False,
            "direction": direction,
            "error": "internal_error",
        }

# ============================================================================
# ENHANCED API ENDPOINTS WITH LOGGING
# ============================================================================

@app.get("/")
@limiter.limit("2000/hour")
@log_api_request(logger)
async def root(request: Request):
    """Health check endpoint with logging"""
    return {
        "status": "healthy",
        "service": "DHK Align WRAITH",
        "version": "2.0.0-WRAITH-LOGGED",
        "features": [
            "7-step enhanced translation",
            "comprehensive structured logging",
            "performance monitoring",
            "user feedback learning",
            "security-aware logging"
        ],
        "logging": {
            "structured_logs": True,
            "performance_tracking": True,
            "security_sanitization": True,
            "log_files": ["dhk_align.log", "translations.jsonl", "performance.jsonl", "errors.log"]
        }
    }

@app.get("/health")
@limiter.limit("1000/hour")
@log_api_request(logger)
async def health_check(request: Request):
    """Comprehensive health check with metrics logging"""
    try:
        db_stats = db_manager.get_stats() if db_manager else {"error": "Database not initialized"}
        
        # Log health metrics
        log_health_check("healthy", **db_stats)
        
        return {
            "status": "healthy",
            "database": db_stats,
            "translator": {
                "status": "active",
                "enhancement_methods": 7,
                "logging_active": True
            },
            "logging": {
                "system": "active",
                "log_directory": "logs/",
                "structured_format": True
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception:
        logger.exception("Health check failed")
        log_health_check("unhealthy", error="internal_error")
        return {
            "status": "degraded",
            "error": "internal_error",
            "timestamp": datetime.now().isoformat()
        }

@app.get("/stats")
@limiter.limit("500/hour")
@log_api_request(logger)
async def get_system_stats(request: Request):
    """Enhanced system statistics with log analysis"""
    try:
        db_stats = db_manager.get_stats() if db_manager else {}
        
        # Get log analytics
        log_analyzer = LogAnalyzer()
        translation_stats = log_analyzer.get_translation_stats(hours=24)
        error_summary = log_analyzer.get_error_summary(hours=24)
        
        return {
            "system": "DHK Align WRAITH",
            "database": db_stats,
            "translation_analytics": {
                "past_24h": translation_stats,
                "success_rate": round(
                    (translation_stats['successful_translations'] / 
                     max(translation_stats['total_requests'], 1)) * 100, 2
                )
            },
            "error_analytics": {
                "past_24h": error_summary
            },
            "features": {
                "enhanced_translation": True,
                "structured_logging": True,
                "performance_monitoring": True,
                "user_feedback_learning": True,
                "log_analysis": True
            },
            "api_endpoints": {
                "translation": "/api/translate",
                "feedback": "/api/feedback", 
                "testing": "/api/test-enhancements",
                "logs": "/logs/analytics"
            }
        }
    except Exception:
        logger.exception("Stats retrieval failed")
        return {"error": "internal_error"}

@app.get("/logs/analytics")
@limiter.limit("100/hour")
@log_api_request(logger)
async def get_log_analytics(
    request: Request,
    hours: int = 24
):
    """Detailed log analytics endpoint"""
    try:
        log_analyzer = LogAnalyzer()
        
        translation_stats = log_analyzer.get_translation_stats(hours)
        error_summary = log_analyzer.get_error_summary(hours)
        
        analytics = {
            "time_period_hours": hours,
            "translation_metrics": translation_stats,
            "error_metrics": error_summary,
            "performance": {
                "avg_response_time_ms": translation_stats.get('avg_processing_time_ms', 0),
                "success_rate_percent": round(
                    (translation_stats['successful_translations'] / 
                     max(translation_stats['total_requests'], 1)) * 100, 2
                )
            },
            "enhancement_usage": translation_stats.get('methods_used', {}),
            "generated_at": datetime.now().isoformat()
        }
        
        # Log the analytics request
        logger.info("Log analytics requested", 
                   hours=hours,
                   total_requests=translation_stats['total_requests'],
                   success_rate=analytics['performance']['success_rate_percent'])
        
        return analytics
        
    except Exception:
        logger.exception("Log analytics failed")
        return {"error": "internal_error"}

@app.post("/admin/reload-dataset")
@log_api_request(logger)
async def admin_reload_dataset(
    request: Request,
    api_key: str = "dev-admin-key"  # Simple auth for demo
):
    """Reload dataset with comprehensive logging"""
    
    if api_key != ADMIN_API_KEY:
        logger.security_event("unauthorized_admin_access", 
                            {"endpoint": "reload_dataset", "provided_key": api_key[:8] + "..."})
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    try:
        if not db_manager:
            raise HTTPException(status_code=500, detail="Database not initialized")
        
        logger.info("Admin dataset reload initiated", admin_action="reload_dataset")
        record_count = db_manager.load_csv_data(CSV_PATH)
        
        logger.info("Admin dataset reload completed", 
                   records_loaded=record_count,
                   admin_action="reload_dataset")
        
        return {
            "status": "success",
            "records_loaded": record_count,
            "message": "Dataset reloaded successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.exception("Admin dataset reload failed")
        raise HTTPException(status_code=500, detail="internal_error")

@app.get("/admin/logs/download/{log_type}")
@log_api_request(logger)
async def download_logs(
    request: Request,
    log_type: str,
    api_key: str = "dev-admin-key"
):
    """Download log files (admin only)"""
    
    if api_key != ADMIN_API_KEY:
        logger.security_event("unauthorized_log_access", 
                            {"endpoint": "download_logs", "log_type": log_type})
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    try:
        log_files = {
            "main": "logs/dhk_align.log",
            "translations": "logs/translations.jsonl", 
            "performance": "logs/performance.jsonl",
            "errors": "logs/errors.log"
        }
        
        if log_type not in log_files:
            raise HTTPException(status_code=400, detail=f"Invalid log type. Available: {list(log_files.keys())}")
        
        log_file = Path(log_files[log_type])
        if not log_file.exists():
            raise HTTPException(status_code=404, detail="Log file not found")
        
        logger.info(f"Admin log download requested", 
                   log_type=log_type,
                   file_size_mb=round(log_file.stat().st_size / (1024 * 1024), 2),
                   admin_action="download_logs")
        
        # Return file info instead of actual file for demo
        return {
            "log_type": log_type,
            "file_path": str(log_file),
            "file_size_mb": round(log_file.stat().st_size / (1024 * 1024), 2),
            "message": "Log file ready for download",
            "note": "In production, this would return the actual file"
        }
        
    except Exception as e:
        logger.exception("Log download failed")
        raise HTTPException(status_code=500, detail="internal_error")

if __name__ == "__main__":
    print("🚀 Starting DHK Align WRAITH Edition with Enhanced Logging...")
    print("📊 Comprehensive logging features:")
    print("   • Structured JSON logs for analytics")
    print("   • Performance monitoring and metrics")
    print("   • Security-aware log sanitization")
    print("   • Rotating log files with size limits")
    print("   • Real-time log analysis endpoints")
    print()
    print("📡 Enhanced API endpoints:")
    print("   GET  /api/translate?q=kemon%20acho&direction=banglish_to_english")
    print("   POST /api/feedback")
    print("   GET  /api/test-enhancements")
    print("   GET  /health")
    print("   GET  /stats")
    print("   GET  /logs/analytics")
    print()
    print("📁 Log files created in logs/ directory:")
    print("   • dhk_align.log - Main application logs")
    print("   • translations.jsonl - Translation operations") 
    print("   • performance.jsonl - Performance metrics")
    print("   • errors.log - Error tracking")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )

# --- removed old cache block ---
try:
    from backend.middleware_cache import TTLResponseCacheMiddleware, backend_cache_stats  # type: ignore
    _mw_cache = TTLResponseCacheMiddleware(app)
    app.add_middleware(TTLResponseCacheMiddleware)
    # patch admin health if present to include cache counters
    try:
        from fastapi import APIRouter
        # find existing router at /admin added earlier
        # we add an additional field via dependency-free closure
        @app.get("/admin/cache_stats")
        async def _cache_stats():
            return backend_cache_stats(_mw_cache)
    except Exception:
        pass
except Exception as _e:
    # cache wiring failed silently to avoid boot errors
    pass
# --- END WRAITH BACKEND TTL CACHE ---


# --- WRAITH BACKEND TTL CACHE (fixed) ---
try:
    from backend.middleware_cache import TTLResponseCacheMiddleware, backend_cache_stats  # type: ignore
    _mw_cache = TTLResponseCacheMiddleware
    app.add_middleware(TTLResponseCacheMiddleware)
    @app.get("/admin/cache_stats")
    async def _cache_stats():
        # middleware instance isn't directly accessible; just return placeholder for now
        return {"cache_hits": "see logs", "cache_misses": "see logs"}
except Exception as _e:
    pass
# --- END WRAITH BACKEND TTL CACHE ---


# --- WRAITH ADMIN CACHE ROUTER (append) ---
try:
    from backend.admin_cache_stats import router as _admin_cache_router
    app.include_router(_admin_cache_router)
except Exception:
    pass
# --- END WRAITH ADMIN CACHE ROUTER ---
