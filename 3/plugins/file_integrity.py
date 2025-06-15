import os
import hashlib
import sqlite3
import time
import sys
import datetime
import shutil
from modules._LoggerModule import setup_logging as _setup_logging
import inquirer
import threading

logger = _setup_logging("FIM")
logger.debug(f"imported, id: {id(sys.modules[__name__])}")

DB_NAME = "integrity.db"
SCAN_DIR = "."
CHECK_INTERVAL = 1
IGNORED_FILES = {DB_NAME}
IGNORED_DIRS = {"logs", "backups", "__pycache__"}
BACKUP_BASE_DIR = "./backups"
DIRECTORIES_TO_BACKUP = [
    "./data",
    "./cogs",
    "./required_cogs",
    "./modules",
    "./plugins",
]

# Ensure backup base directory exists
if not os.path.exists(BACKUP_BASE_DIR):
    os.makedirs(BACKUP_BASE_DIR)

if os.path.exists(DB_NAME):
    os.remove(DB_NAME)

logger.debug("File Integrity Monitor initiated")


def _get_file_hash(file_path):
    """Generate SHA-256 hash of a file"""
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(4096):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logger.exception(f"Error hashing {file_path}: {e}")
        return None


def _initialize_database():
    """Create database and table if not exists"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            hash TEXT NOT NULL
        )
    """
    )
    conn.commit()
    conn.close()


def _get_free_space(directory):
    """Returns the free space of a directory in bytes"""
    try:
        total, used, free = shutil.disk_usage(directory)
        return free
    except Exception as e:
        logger.exception(f"Error getting free space for {directory}: {e}")
        return 0


def _create_backup(directory):
    """Creates a backup of the specified directory."""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_dir = os.path.join(BACKUP_BASE_DIR, f"backup_{timestamp}")

        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        # Copy the directory to the backup location
        shutil.copytree(
            directory, os.path.join(backup_dir, os.path.basename(directory))
        )
        logger.info(f"Backup successful for {directory} at {backup_dir}")
    except Exception as e:
        logger.exception(f"Error while creating backup for {directory}: {e}")


def _backup_directories():
    """Backup specified directories before scanning for file integrity"""
    for directory in DIRECTORIES_TO_BACKUP:
        if os.path.exists(directory):
            _create_backup(directory)
        else:
            logger.warning(f"Directory {directory} does not exist, skipping backup.")


def _restore_from_backup(deleted_file):
    """Attempts to restore a deleted file from backups"""
    logger.info(f"Attempting to restore deleted file: {deleted_file}")

    # Check backup directories for the deleted file
    for backup_dir in os.listdir(BACKUP_BASE_DIR):
        backup_path = os.path.join(BACKUP_BASE_DIR, backup_dir, deleted_file)

        if os.path.exists(backup_path):
            logger.info(f"Backup found for {deleted_file} at {backup_path}")
            questions = [
                inquirer.Confirm(
                    "restore",
                    message=f"Do you want to restore {deleted_file} from backup?",
                    default=True,
                ),
            ]
            answers = inquirer.prompt(questions)
            user_input = "y" if answers["restore"] else "n"

            if user_input.lower() == "y":
                try:
                    # Restore the file from the backup location
                    restore_path = os.path.join(SCAN_DIR, deleted_file)
                    shutil.copy(backup_path, restore_path)
                    logger.info(
                        f"Successfully restored {deleted_file} to {restore_path}"
                    )
                except Exception as e:
                    logger.error(f"Failed to restore {deleted_file}: {e}")
                return
            else:
                logger.info(f"Restoration of {deleted_file} cancelled by user.")
                return

    logger.warning(f"No backup found for {deleted_file}. Restoration failed.")


def _scan_and_store():
    _backup_directories()

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    for root, dirs, files in os.walk(SCAN_DIR):
        # Remove ignored directories from traversal
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

        for file in files:
            if file in IGNORED_FILES:
                continue  # Skip ignored files

            file_path = os.path.join(root, file)
            file_hash = _get_file_hash(file_path)
            if file_hash:
                cursor.execute(
                    "INSERT OR REPLACE INTO files (path, hash) VALUES (?, ?)",
                    (file_path, file_hash),
                )

    conn.commit()
    conn.close()
    logger.debug("Initial scan completed. Database updated.")


def _get_file_details(file_path):
    """Retrieve file details including size, last modification time, and hash"""
    try:
        file_size = os.path.getsize(file_path)  # Get file size in bytes
        last_modified = datetime.datetime.fromtimestamp(
            os.path.getmtime(file_path)
        ).strftime(
            "%Y-%m-%d %H:%M:%S"
        )  # Get last modified time
        file_hash = _get_file_hash(file_path)  # Get file hash
        return file_size, last_modified, file_hash
    except Exception as e:
        logger.exception(f"Error retrieving details for {file_path}: {e}")
        return None, None, None


def _check_integrity():
    """Continuously check for file changes every 30 seconds"""
    while True:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        stored_files = {
            row[0]: row[1] for row in cursor.execute("SELECT path, hash FROM files")
        }
        current_files = {}

        for root, dirs, files in os.walk(SCAN_DIR):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]  # Exclude ignored dirs

            for file in files:
                if file in IGNORED_FILES:
                    continue  # Skip ignored files

                file_path = os.path.join(root, file)
                file_hash = _get_file_hash(file_path)
                if file_hash:
                    current_files[file_path] = file_hash

        modified_files = []
        deleted_files = []
        new_files = []

        for path, old_hash in stored_files.items():
            if path not in current_files:
                deleted_files.append(path)
            elif current_files[path] != old_hash:
                modified_files.append(path)

        for path in current_files.keys():
            if path not in stored_files:
                new_files.append(path)

        # Display results
        if modified_files:
            logger.warning("Modified file(s) detected:")
            for file in modified_files:
                size, modified_time, file_hash = _get_file_details(file)
                old_hash = stored_files.get(file)
                logger.warning(f"  • Path: {file}")
                logger.warning(f"    ├─ Size: {size} bytes")
                logger.warning(f"    ├─ Old Hash: {old_hash}")
                logger.warning(f"    └─ New Hash: {file_hash}")

        if deleted_files:
            logger.critical("Following file(s) have been corrupted or removed:")
            for file in deleted_files:
                logger.critical(f"  • Path: {file}")
                _restore_from_backup(file)  # Attempt to restore deleted file

        if new_files:
            logger.info("New file(s) detected:")
            for file in new_files:
                size, modified_time, file_hash = _get_file_details(file)
                logger.info(f"  • Path: {file}")
                logger.info(f"    ├─ Size: {size} bytes")
                logger.info(f"    └─ Hash: {file_hash}")

        cursor.execute("DELETE FROM files")
        for path, file_hash in current_files.items():
            cursor.execute(
                "INSERT INTO files (path, hash) VALUES (?, ?)", (path, file_hash)
            )

        conn.commit()
        conn.close()

        time.sleep(CHECK_INTERVAL)


def _run():
    _initialize_database()
    _scan_and_store()
    _check_integrity()


def post_init():
    thread = threading.Thread(target=_run)
    thread.daemon = True
    thread.start()