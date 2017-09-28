CREATE TABLE highlight_marker (
    id SERIAL NOT NULL PRIMARY KEY,
    broadcaster VARCHAR NOT NULL,
    broadcastId BIGINT NOT NULL,
    broadcastTime TIMESTAMP NOT NULL,
    markedTime TIMESTAMP NOT NULL,
    reason VARCHAR NULL
);
CREATE INDEX highlight_broadcaster ON highlight_marker (broadcaster);
