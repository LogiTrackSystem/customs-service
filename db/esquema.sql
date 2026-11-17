-- Esquema de customs_db (customs-service): SQL generado por 'alembic upgrade head --sql' a partir de alembic/versions.
-- Crea todas las tablas, secuencias y restricciones. No contiene datos.
BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 4624fcede4f2

CREATE TABLE declaraciones_aduaneras (
    id UUID NOT NULL, 
    envio_id UUID NOT NULL, 
    pais_origen VARCHAR NOT NULL, 
    pais_destino VARCHAR NOT NULL, 
    documentos JSONB NOT NULL, 
    estado VARCHAR NOT NULL, 
    motivo_retencion VARCHAR, 
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    actualizado_en TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_declaraciones_aduaneras_envio_id ON declaraciones_aduaneras (envio_id);

INSERT INTO alembic_version (version_num) VALUES ('4624fcede4f2') RETURNING alembic_version.version_num;

-- Running upgrade 4624fcede4f2 -> 7a3edd642bf6

UPDATE alembic_version SET version_num='7a3edd642bf6' WHERE alembic_version.version_num = '4624fcede4f2';

COMMIT;

