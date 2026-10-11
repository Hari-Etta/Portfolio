
    
    



select customer_zip_code_prefix
from `dbt-medallion`.`silver`.`silver_geolocation`
where customer_zip_code_prefix is null


