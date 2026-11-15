{{ config(schema='ads', alias='transaction_detail') }}

SELECT * FROM {{ ref('dws_transaction_detail') }}
