SELECT 'CREATE DATABASE quant_data_hub'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = 'quant_data_hub'
)\gexec

SELECT 'CREATE DATABASE quant_factor_lab'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = 'quant_factor_lab'
)\gexec

SELECT 'CREATE DATABASE quant_factor_validation'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = 'quant_factor_validation'
)\gexec
