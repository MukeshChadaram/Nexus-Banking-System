CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50),
    target VARCHAR(50),
    amount FLOAT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dummy Data
INSERT INTO transactions (source, target, amount) VALUES 
('Cartel_Ops', 'Shell_Alpha', 1000000),
('Shell_Alpha', 'Shell_Beta', 990000),
('Shell_Beta', 'Clean_Co', 980000),
('Clean_Co', 'Cartel_Ops', 150000);