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
        case_id INTEGER NOT NULL,
        partition_offset INTEGER NOT NULL,
        fs_type TEXT,
        label TEXT,
        block_size INTEGER,
        block_count INTEGER,
        FOREIGN KEY (case_id) REFERENCES case_info(case_id)
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

    -- Logs de análisis
    CREATE TABLE IF NOT EXISTS analysis_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        message TEXT NOT NULL,
        level TEXT DEFAULT 'INFO',
        FOREIGN KEY (case_id) REFERENCES case_info(case_id)
    );

    -- Etiquetas manuales
    CREATE TABLE IF NOT EXISTS user_tag (
        tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_id INTEGER NOT NULL,
        tag TEXT NOT NULL,
        comment TEXT,
        FOREIGN KEY (entry_id) REFERENCES filesystem_entry(entry_id)
    );

    -- Entradas del registro de Windows
    CREATE TABLE IF NOT EXISTS registry_entries (
        reg_id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,
        hive TEXT NOT NULL,
        key_path TEXT NOT NULL,
        value_name TEXT,
        value_data TEXT,
        value_type TEXT,
        last_modified DATETIME,
        FOREIGN KEY (case_id) REFERENCES case_info(case_id)
    );

    -- Logs de eventos de Windows
    CREATE TABLE IF NOT EXISTS event_logs (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,
        log_name TEXT,
        record_id INTEGER,
        source TEXT,
        event_code INTEGER,
        level TEXT,
        message TEXT,
        event_time DATETIME,
        FOREIGN KEY (case_id) REFERENCES case_info(case_id)
    );

    -- Conexiones de red (si se extrae información de Prefetch o Volatility)
    CREATE TABLE IF NOT EXISTS net_connections (
        conn_id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,
        process_name TEXT,
        local_address TEXT,
        local_port INTEGER,
        remote_address TEXT,
        remote_port INTEGER,
        protocol TEXT,
        timestamp DATETIME,
        FOREIGN KEY (case_id) REFERENCES case_info(case_id)
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
    CREATE INDEX IF NOT EXISTS idx_event_time ON event_logs(event_time);
    CREATE INDEX IF NOT EXISTS idx_registry_modified ON registry_entries(last_modified);
    CREATE INDEX IF NOT EXISTS idx_net_time ON net_connections(timestamp);
    """)

    conn.commit()
    conn.close()
    print(f"Base de datos forense creada en: {path_db}")



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


def insertar_registry_entry(cursor, case_id, hive, key_path, value_name,
                            value_data, value_type, last_modified):
    cursor.execute("""
    INSERT INTO registry_entries (
        case_id, hive, key_path, value_name, value_data, value_type, last_modified
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        case_id, hive, key_path, value_name, value_data, value_type, last_modified
    ))


def insertar_event_log(cursor, case_id, log_name, record_id, source, event_code,
                       level, message, event_time):
    cursor.execute("""
    INSERT INTO event_logs (
        case_id, log_name, record_id, source, event_code, level, message, event_time
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        case_id, log_name, record_id, source, event_code, level, message, event_time
    ))

def insertar_net_connection(cursor, case_id, process_name, local_address, local_port,
                            remote_address, remote_port, protocol, timestamp):
    cursor.execute("""
    INSERT INTO net_connections (
        case_id, process_name, local_address, local_port,
        remote_address, remote_port, protocol, timestamp
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        case_id, process_name, local_address, local_port,
        remote_address, remote_port, protocol, timestamp
    ))


def insertar_timeline_event(cursor, case_id, source, reference_id, description, timestamp):
    cursor.execute("""
    INSERT INTO unified_timeline (
        case_id, source, reference_id, description, timestamp
    ) VALUES (?, ?, ?, ?, ?)
    """, (
        case_id, source, reference_id, description, timestamp
    ))
