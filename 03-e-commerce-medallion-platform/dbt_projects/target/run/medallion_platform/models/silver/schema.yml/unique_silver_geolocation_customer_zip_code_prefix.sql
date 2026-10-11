
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    customer_zip_code_prefix as unique_field,
    count(*) as n_records

from `dbt-medallion`.`silver`.`silver_geolocation`
where customer_zip_code_prefix is not null
group by customer_zip_code_prefix
having count(*) > 1



  
  
      
    ) dbt_internal_test