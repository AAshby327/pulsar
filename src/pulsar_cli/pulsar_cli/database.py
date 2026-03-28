"""Database management for tracking installed packages."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


class PackageDatabase:
    """SQLite database for tracking installed packages and their files."""

    def __init__(self, db_path: Path):
        """
        Initialize the package database.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS packages (
                name TEXT PRIMARY KEY,
                version TEXT,
                type TEXT,
                category TEXT,
                installed_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS package_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                package_name TEXT,
                file_path TEXT,
                FOREIGN KEY(package_name) REFERENCES packages(name) ON DELETE CASCADE
            )
            """
        )
        conn.commit()
        conn.close()

    def add_package(
        self, name: str, version: str, pkg_type: str, category: str, files: List[str]
    ):
        """
        Add a package to the database.

        Args:
            name: Package name
            version: Package version
            pkg_type: Package type (binary, lsp, nvim_plugin, etc.)
            category: Package category (tool, lsp, plugin, etc.)
            files: List of installed file paths
        """
        conn = sqlite3.connect(self.db_path)
        installed_at = datetime.now().isoformat()

        # Insert package
        conn.execute(
            "INSERT OR REPLACE INTO packages (name, version, type, category, installed_at) VALUES (?, ?, ?, ?, ?)",
            (name, version, pkg_type, category, installed_at),
        )

        # Delete old files for this package (in case of reinstall)
        conn.execute("DELETE FROM package_files WHERE package_name = ?", (name,))

        # Insert files
        for file_path in files:
            conn.execute(
                "INSERT INTO package_files (package_name, file_path) VALUES (?, ?)",
                (name, file_path),
            )

        conn.commit()
        conn.close()

    def remove_package(self, name: str) -> List[str]:
        """
        Remove a package from the database and return its files.

        Args:
            name: Package name

        Returns:
            List of file paths associated with the package
        """
        conn = sqlite3.connect(self.db_path)

        # Get files
        cursor = conn.execute(
            "SELECT file_path FROM package_files WHERE package_name = ?", (name,)
        )
        files = [row[0] for row in cursor.fetchall()]

        # Delete package and files
        conn.execute("DELETE FROM package_files WHERE package_name = ?", (name,))
        conn.execute("DELETE FROM packages WHERE name = ?", (name,))

        conn.commit()
        conn.close()

        return files

    def is_installed(self, name: str) -> bool:
        """
        Check if a package is installed.

        Args:
            name: Package name

        Returns:
            True if package is installed
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM packages WHERE name = ?", (name,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def get_package(self, name: str) -> Optional[Tuple[str, str, str, str, str]]:
        """
        Get package information.

        Args:
            name: Package name

        Returns:
            Tuple of (name, version, type, category, installed_at) or None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT name, version, type, category, installed_at FROM packages WHERE name = ?",
            (name,),
        )
        result = cursor.fetchone()
        conn.close()
        return result

    def list_installed(self) -> List[Tuple[str, str, str, str, str]]:
        """
        List all installed packages.

        Returns:
            List of tuples (name, version, type, category, installed_at)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT name, version, type, category, installed_at FROM packages ORDER BY name"
        )
        results = cursor.fetchall()
        conn.close()
        return results

    def get_package_files(self, name: str) -> List[str]:
        """
        Get files associated with a package.

        Args:
            name: Package name

        Returns:
            List of file paths
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT file_path FROM package_files WHERE package_name = ?", (name,)
        )
        files = [row[0] for row in cursor.fetchall()]
        conn.close()
        return files
