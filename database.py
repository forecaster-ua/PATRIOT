import sqlite3
from datetime import datetime
from typing import Dict, Optional, List
import logging
from pathlib import Path

# Local imports
from config import LOG_DIR
from utils import logger

class SignalDatabase:
    """Handles all database operations for trading signals"""
    
    def __init__(self, db_path: str = 'signals.db'):
        self.db_path = db_path
        self._init_db()
        logger.info(f"Database initialized at {db_path}")

    def _init_db(self) -> None:
        """Initialize database schema"""
        with self._get_connection() as conn:
            conn.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pair TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                signal TEXT NOT NULL,
                current_price REAL NOT NULL,
                entry_price REAL NOT NULL,
                take_profit REAL NOT NULL,
                stop_loss REAL NOT NULL,
                confidence REAL NOT NULL,
                dominance REAL DEFAULT 0.0,
                dominance_change_percent REAL DEFAULT 0.0,
                dominant_timeframe TEXT NOT NULL,
                description TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(pair, timeframe, timestamp)
            )
            ''')
            conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_signal_search 
            ON signals(pair, timeframe, timestamp)
            ''')

    def _get_connection(self) -> sqlite3.Connection:
        """Create thread-safe database connection"""
        return sqlite3.connect(self.db_path, timeout=10)

    def save_signal(self, signal_data: Dict) -> bool:
        """Update required fields to match API response"""
        required_fields = {
    'pair', 'timeframe', 'signal', 'current_price',
    'entry_price', 'take_profit', 'stop_loss', 'confidence',
    'dominance', 'dominance_change_percent', 'dominant_timeframe', 'description'
}
    
        if not all(field in signal_data for field in required_fields):
            missing = [f for f in required_fields if f not in signal_data]
            logger.error(f"Missing required fields: {missing}")
            return False

        query = '''
        INSERT OR REPLACE INTO signals
        (pair, timeframe, signal, current_price, entry_price, take_profit, stop_loss, confidence, dominance, dominance_change_percent, dominant_timeframe, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        params = (
            signal_data['pair'],
            signal_data['timeframe'],
            signal_data['signal'],
            signal_data['current_price'],
            signal_data['entry_price'],
            signal_data['take_profit'],
            signal_data['stop_loss'],
            signal_data['confidence'],
            signal_data.get('dominance', 0.0),
            signal_data.get('dominance_change_percent', 0.0),
            signal_data.get('dominant_timeframe', ''),
            signal_data.get('description', '')
        )

        try:
            with self._get_connection() as conn:
                conn.execute(query, params)
                conn.commit()
            logger.debug(f"Signal saved: {signal_data['pair']} {signal_data['timeframe']}")
            return True
            
        except sqlite3.Error as e:
            logger.error(
                f"Database save failed | Pair: {signal_data['pair']} | "
                f"Error: {str(e)}"
            )
            return False

    def get_latest_signals(self, 
                          pair: Optional[str] = None,
                          timeframe: Optional[str] = None,
                          limit: int = 100) -> List[Dict]:
        """
        Retrieve latest signals with optional filters
        Args:
            pair: Filter by trading pair
            timeframe: Filter by timeframe
            limit: Maximum results to return
        Returns:
            List of signal dictionaries
        """
        query = '''SELECT * FROM signals'''
        conditions = []
        params = []
        
        if pair:
            conditions.append("pair = ?")
            params.append(pair)
        if timeframe:
            conditions.append("timeframe = ?")
            params.append(timeframe)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor]
                
        except sqlite3.Error as e:
            logger.error(f"Database query failed: {str(e)}")
            return []

# Singleton instance for application-wide use
db = SignalDatabase()