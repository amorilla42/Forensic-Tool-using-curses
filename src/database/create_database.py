import sqlite3

def crear_base_de_datos(path_db):
    conn = sqlite3.connect(path_db)
    cursor = conn.cursor()

    cursor.executescript("""
    -- Tabla principal de casos
    CREATE TABLE IF NOT EXISTS case_info (
        case_id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_name TEXT NOT NULL,
        e01_path TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        hash_sha256 TEXT NOT NULL
    );

    -- Tabla de particiones encontradas
    CREATE TABLE IF NOT EXISTS partition_info (
        partition_id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_name INTEGER NOT NULL,
        description TEXT NOT NULL,
        start_offset INTEGER NOT NULL,
        length INTEGER NOT NULL,
        partition_offset INTEGER NOT NULL,
        fs_type TEXT,
        label TEXT,
        block_size INTEGER,
        block_count INTEGER,
        FOREIGN KEY (case_name) REFERENCES case_info(case_name)
    );

    -- Entradas del sistema de archivos
    CREATE TABLE IF NOT EXISTS filesystem_entry (
        entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
        partition_id INTEGER NOT NULL,
        full_path TEXT NOT NULL,
        name TEXT NOT NULL,
        extension TEXT,
        type TEXT NOT NULL,
        size INTEGER,
        inode INTEGER,
        mtime DATETIME,
        atime DATETIME,
        ctime DATETIME,
        crtime DATETIME,
        sha256 TEXT,
        is_deleted BOOLEAN DEFAULT 0,
        is_carved BOOLEAN DEFAULT 0,
        is_suspicious BOOLEAN DEFAULT 0,
        FOREIGN KEY (partition_id) REFERENCES partition_info(partition_id)
    );

    -- Hashes de archivos
    CREATE TABLE IF NOT EXISTS file_hash (
        hash_id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_id INTEGER NOT NULL,
        sha256 TEXT NOT NULL,
        md5 TEXT,
        FOREIGN KEY (entry_id) REFERENCES filesystem_entry(entry_id)
    );



    -- Línea de tiempo unificada
    CREATE TABLE IF NOT EXISTS unified_timeline (
        timeline_id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,
        source TEXT NOT NULL, -- 'fs', 'registry', 'event_log', 'network'
        reference_id INTEGER, -- ID relacionado con la tabla original
        description TEXT,
        timestamp DATETIME NOT NULL,
        FOREIGN KEY (case_id) REFERENCES case_info(case_id)
    );

    -- Índices para rendimiento
    CREATE INDEX IF NOT EXISTS idx_full_path ON filesystem_entry(full_path);
    CREATE INDEX IF NOT EXISTS idx_extension ON filesystem_entry(extension);
    CREATE INDEX IF NOT EXISTS idx_deleted ON filesystem_entry(is_deleted);
    CREATE INDEX IF NOT EXISTS idx_mtime ON filesystem_entry(mtime);
    CREATE INDEX IF NOT EXISTS idx_crtime ON filesystem_entry(crtime);
    CREATE INDEX IF NOT EXISTS idx_suspicious ON filesystem_entry(is_suspicious);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_hash_sha256 ON file_hash(sha256);
    CREATE INDEX IF NOT EXISTS idx_timeline_time ON unified_timeline(timestamp);
    """)

    conn.commit()
    conn.close()

def insertar_case_info(cursor, case_name, e01_path, hash_sha256):
    cursor.execute("""
    INSERT INTO case_info (case_name, e01_path, hash_sha256)
    VALUES (?, ?, ?)
    """, (case_name, e01_path, hash_sha256))
    return cursor.lastrowid



def insertar_partition_info(cursor, case_id, description, start_offset, length, partition_offset, fs_type, label,
                            block_size, block_count):
    cursor.execute("""
    INSERT INTO partition_info (case_name, description, start_offset, length, partition_offset, fs_type, label, block_size, block_count)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (case_id, description, start_offset, length, partition_offset, fs_type, label, block_size, block_count))
    return cursor.lastrowid


def insertar_filesystem_entry(cursor, partition_id, full_path, name, extension, tipo, size,
                              inode, mtime=None, atime=None, ctime=None, crtime=None, sha256=None,
                              is_deleted=False, is_carved=False, is_suspicious=False):
    cursor.execute("""
    INSERT INTO filesystem_entry (
        partition_id, full_path, name, extension, type, size, inode,
        mtime, atime, ctime, crtime, sha256, is_deleted, is_carved, is_suspicious
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        partition_id, full_path, name, extension, tipo, size, inode,
        mtime, atime, ctime, crtime, sha256, is_deleted, is_carved, is_suspicious
    ))
    return cursor.lastrowid

def insertar_file_hash(cursor, entry_id, sha256, md5=None):
    cursor.execute("""
    INSERT INTO file_hash (entry_id, sha256, md5)
    VALUES (?, ?, ?)
    """, (entry_id, sha256, md5))



def insertar_timeline_event(cursor, case_id, source, reference_id, description, timestamp):
    cursor.execute("""
    INSERT INTO unified_timeline (
        case_id, source, reference_id, description, timestamp
    ) VALUES (?, ?, ?, ?, ?)
    """, (
        case_id, source, reference_id, description, timestamp
    ))
