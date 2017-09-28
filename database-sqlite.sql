CREATE TABLE highlight_marker (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    broadcaster VARCHAR NOT NULL,
    broadcastId INTEGER NOT NULL,
    broadcastTime TIMESTAMP NOT NULL,
    markedTime TIMESTAMP NOT NULL,
    reason VARCHAR NULL
);
CREATE INDEX highlight_broadcaster ON highlight_marker (broadcaster);
