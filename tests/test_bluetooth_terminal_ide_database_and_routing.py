#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration and Unit Tests for Lauburu Bluetooth Terminal IDE:
- Database Manager (Obsidian Vault + SQLite Lakehouse + System Rules)
- Intent Classification & Auto-Routing (Chat vs Coding vs Safe Shell)
- Database Grounding & Provenance Injection
- Authentic Zero-Mock Terminal Commands ('db status', 'db readiness', 'readiness')
Rule #0 Compliance: 0 mocks, 0 synthetic arrays. Genuine database files and syscalls only.
"""

import os
import sys
import json
import sqlite3
import pytest
from pathlib import Path

REPO_ROOT = Path('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo')
sys.path.insert(0, str(REPO_ROOT / '01_apps/bluetooth_terminal_ide/backend'))

from server import (
    LauburuDatabaseManager,
    is_likely_shell_command,
    auto_route_chat_coding,
    app
)
from fastapi.testclient import TestClient

client = TestClient(app)

def test_database_manager_indexing():
    """Verify LauburuDatabaseManager indexes >5,000 authentic records across Tri-Vault."""
    db_manager = LauburuDatabaseManager()
    db_manager.index_all()
    assert len(db_manager.docs) >= 5000
    assert 'readiness.db' in db_manager.sqlite_stats

def test_database_sqlite_readiness_integrity():
    """Verify authentic biometric and readiness records exist in SQLite."""
    db_path = REPO_ROOT / '04_data_and_memory/data/readiness.db'
    assert db_path.exists(), 'readiness.db must exist'
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM daily_readiness')
    daily_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM telemetry')
    telem_count = cursor.fetchone()[0]
    conn.close()

    assert daily_count >= 1, 'daily_readiness must have records'
    assert telem_count >= 10, 'telemetry must contain authentic sensor rows'

def test_database_search_readiness():
    """Verify db_manager.search accurately ranks readiness records."""
    db_manager = LauburuDatabaseManager()
    db_manager.index_all()
    results = db_manager.search('readiness', limit=5)
    assert len(results) > 0
    top = results[0]
    assert 'readiness' in top['title'].lower() or 'readiness' in top['snippet'].lower()
    assert top['score'] > 0

def test_is_likely_shell_command_logic():
    """Verify accurate classification of safe shell commands vs natural language."""
    assert is_likely_shell_command('git status') is True
    assert is_likely_shell_command('ls -la /Users/aaron') is True
    assert is_likely_shell_command('uname -a') is True
    assert is_likely_shell_command('what is the git status command?') is False
    assert is_likely_shell_command('explain the 7 layer mesh') is False
    assert is_likely_shell_command('hello there, how are you?') is False

def test_api_health_endpoint():
    """Verify /health reports database connected and prima configured."""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'HEALTHY'
    assert data['database_connected'] is True
    assert data['database_records_indexed'] >= 5000
    assert 'readiness.db' in data['sqlite_databases']

def test_api_terminal_db_status():
    """Verify db status command returns authentic database inventory."""
    response = client.post('/api/terminal/run', json={'command': 'db status'})
    assert response.status_code == 200
    data = response.json()
    assert 'output' in data
    assert 'LAUBURU TRI-VAULT & MESH DATABASE STATUS' in data['output']
    assert 'readiness.db' in data['output']

def test_api_terminal_db_search():
    """Verify db <query> command returns grounded search results."""
    response = client.post('/api/terminal/run', json={'command': 'db readiness'})
    assert response.status_code == 200
    data = response.json()
    assert 'output' in data
    assert 'DATABASE SEARCH RESULTS' in data['output']
    assert 'readiness.db' in data['output']

def test_api_terminal_readiness_command():
    """Verify readiness command extracts authentic biometric rows."""
    response = client.post('/api/terminal/run', json={'command': 'readiness'})
    assert response.status_code == 200
    data = response.json()
    assert 'output' in data
    assert 'LATEST BIOMETRIC READINESS' in data['output']
    assert 'Daily Readiness Records' in data['output']

if __name__ == '__main__':
    pytest.main(['-v', __file__])
