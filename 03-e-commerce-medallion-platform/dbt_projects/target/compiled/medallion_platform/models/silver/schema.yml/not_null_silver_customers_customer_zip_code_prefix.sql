
    
    



select customer_zip_code_prefix
from `dbt-medallion`.`silver`.`silver_customers`
where customer_zip_code_prefix is null


