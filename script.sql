CREATE EXTENSION IF NOT EXISTS postgis;

DROP TABLE IF EXISTS se_tient_le;
DROP TABLE IF EXISTS Localisee_a;
DROP TABLE IF EXISTS Presente;
DROP TABLE IF EXISTS Disponible_en_Langue;
DROP TABLE IF EXISTS A_pour_debouche;
DROP TABLE IF EXISTS Requiert;
DROP TABLE IF EXISTS Categorise;
DROP TABLE IF EXISTS Propose;
DROP TABLE IF EXISTS Supporte;
DROP TABLE IF EXISTS JPO;
DROP TABLE IF EXISTS Adresse;
DROP TABLE IF EXISTS Contact;
DROP TABLE IF EXISTS Etablissement;
DROP TABLE IF EXISTS Date;
DROP TABLE IF EXISTS Formation;
DROP TABLE IF EXISTS Mention;
DROP TABLE IF EXISTS Prerequis;
DROP TABLE IF EXISTS Debouches;
DROP TABLE IF EXISTS Langue;

CREATE TABLE Etablissement (
    id_Etablissement VARCHAR(8) NOT NULL,
    nom_Etablissement VARCHAR(255),
    type_Etablissement VARCHAR(255),
    statut_Etablissement VARCHAR(255),
    Est_Internat BOOLEAN DEFAULT FALSE,
    Hebergement_Etablissement TEXT,
    contact_id_contact INT,
    PRIMARY KEY (id_Etablissement)
);

CREATE TABLE Adresse (
    id_Adresse SERIAL NOT NULL,
    code_postal_Adresse INT,
    n_rue_Adresse INT,
    nom_rue_Adresse VARCHAR(255),
    ville_Adresse VARCHAR(100),
    longitude_Adresse FLOAT,
    latitude_Adresse FLOAT,
    geom GEOGRAPHY(Point, 4326),
    id_Etablissement VARCHAR(8),
    PRIMARY KEY (id_Adresse),
    FOREIGN KEY (id_Etablissement) REFERENCES Etablissement(id_Etablissement) ON DELETE CASCADE
);

CREATE TABLE JPO (
    id_JPO SERIAL NOT NULL,
    description_JPO TEXT,
    id_Etablissement VARCHAR(8),
    PRIMARY KEY (id_JPO),
    FOREIGN KEY (id_Etablissement) REFERENCES Etablissement(id_Etablissement) ON DELETE CASCADE,
    CONSTRAINT unique_id_etablissement UNIQUE (id_Etablissement)
);

CREATE TABLE Mention (
    id_mention SERIAL NOT NULL,
    nom_mention VARCHAR(40),
    description_Mention TEXT,
    PRIMARY KEY (id_mention)
);

CREATE TABLE Formation (
    id_Formation SERIAL,
    titre_Formation VARCHAR(255),
    niveau_Formation VARCHAR(150),
    duree_Formation INT,
    duree_du_stage_Formation INT,
    possibilite_alternance_Formation BOOLEAN,
    modalite_Formation TEXT,
    page_web_Formation TEXT,
    PRIMARY KEY (id_Formation)
);

CREATE TABLE Prerequis (
    id_prerequis SERIAL NOT NULL,
    nom_prerequis VARCHAR(40),
    PRIMARY KEY (id_prerequis)
);

CREATE TABLE Debouches (
    id_debouches SERIAL NOT NULL,
    nom_debouches VARCHAR(40),
    description_debouches TEXT,
    PRIMARY KEY (id_debouches)
);

CREATE TABLE Langue (
    id_Langue SERIAL NOT NULL,
    nom_Langue VARCHAR(40),
    PRIMARY KEY (id_Langue)
);

CREATE TABLE Contact (
    id_Contact SERIAL NOT NULL,
    num_tel_Etablissement VARCHAR(20),
    site_web_Etablissement VARCHAR(100) UNIQUE,
    etablissement_id_etablissement VARCHAR(8) UNIQUE,
    PRIMARY KEY (id_Contact),
    FOREIGN KEY (etablissement_id_etablissement) REFERENCES Etablissement(id_Etablissement) ON DELETE CASCADE
);

CREATE TABLE Date (
    id_Date SERIAL PRIMARY KEY,
    date_Date DATE UNIQUE
);

CREATE TABLE Propose (
    id_Etablissement VARCHAR(8) NOT NULL,
    id_Formation INT,
    titre_Formation VARCHAR(255) NOT NULL,
    PRIMARY KEY (id_Etablissement, id_Formation),
    FOREIGN KEY (id_Etablissement) REFERENCES Etablissement(id_Etablissement) ON DELETE CASCADE,
    FOREIGN KEY (id_Formation) REFERENCES Formation(id_Formation) ON DELETE CASCADE,
    CONSTRAINT unique_etablissement_titre UNIQUE (id_Etablissement, titre_Formation)
);

CREATE TABLE Categorise (
    id_Formation INT,
    id_mention INT NOT NULL,
    couts_Categorise FLOAT,
    PRIMARY KEY (id_Formation, id_mention),
    FOREIGN KEY (id_Formation) REFERENCES Formation(id_Formation) ON DELETE CASCADE,
    FOREIGN KEY (id_mention) REFERENCES Mention(id_mention) ON DELETE CASCADE
);

CREATE TABLE Requiert (
    id_Formation INT,
    id_prerequis INT NOT NULL,
    PRIMARY KEY (id_Formation, id_prerequis),
    FOREIGN KEY (id_Formation) REFERENCES Formation(id_Formation) ON DELETE CASCADE,
    FOREIGN KEY (id_prerequis) REFERENCES Prerequis(id_prerequis) ON DELETE CASCADE
);

CREATE TABLE A_pour_debouche (
    id_Formation INT,
    id_debouches INT NOT NULL,
    PRIMARY KEY (id_Formation, id_debouches),
    FOREIGN KEY (id_Formation) REFERENCES Formation(id_Formation) ON DELETE CASCADE,
    FOREIGN KEY (id_debouches) REFERENCES Debouches(id_debouches) ON DELETE CASCADE
);

CREATE TABLE Disponible_en_Langue (
    id_Langue INT NOT NULL,
    id_Formation INT,
    PRIMARY KEY (id_Langue, id_Formation),
    FOREIGN KEY (id_Langue) REFERENCES Langue(id_Langue) ON DELETE CASCADE,
    FOREIGN KEY (id_Formation) REFERENCES Formation(id_Formation) ON DELETE CASCADE
);

CREATE TABLE Presente (
    id_Formation INT,
    id_JPO INT NOT NULL,
    PRIMARY KEY (id_Formation, id_JPO),
    FOREIGN KEY (id_Formation) REFERENCES Formation(id_Formation) ON DELETE CASCADE,
    FOREIGN KEY (id_JPO) REFERENCES JPO(id_JPO) ON DELETE CASCADE
);

CREATE TABLE Localisee_a (
    id_JPO INT NOT NULL,
    id_Adresse INT NOT NULL,
    PRIMARY KEY (id_JPO, id_Adresse),
    FOREIGN KEY (id_JPO) REFERENCES JPO(id_JPO) ON DELETE CASCADE,
    FOREIGN KEY (id_Adresse) REFERENCES Adresse(id_Adresse) ON DELETE CASCADE
);

CREATE TABLE Supporte (
    id_Etablissement VARCHAR(8) NOT NULL,
    id_Langue INT NOT NULL,
    PRIMARY KEY (id_Etablissement, id_Langue),
    FOREIGN KEY (id_Etablissement) REFERENCES Etablissement(id_Etablissement) ON DELETE CASCADE,
    FOREIGN KEY (id_Langue) REFERENCES Langue(id_Langue) ON DELETE CASCADE
);

CREATE TABLE se_tient_le (
    id_JPO INT NOT NULL,
    id_Date INT NOT NULL,
    PRIMARY KEY (id_JPO, id_Date),
    FOREIGN KEY (id_JPO) REFERENCES JPO(id_JPO) ON DELETE CASCADE,
    FOREIGN KEY (id_Date) REFERENCES Date(id_Date) ON DELETE CASCADE
);

-- Adding unique constraint after table creation
ALTER TABLE Adresse
    ADD CONSTRAINT unique_address UNIQUE (id_Etablissement, code_postal_Adresse, n_rue_Adresse, nom_rue_Adresse);
