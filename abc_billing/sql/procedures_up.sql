DELIMITER $$
DROP FUNCTION IF EXISTS int_to_date $$
CREATE FUNCTION int_to_date(date_int INT)
RETURNS DATE
BEGIN
    DECLARE result_date DATE;
    IF date_int IS NULL OR date_int < 19000101 OR date_int > 99991231 OR LENGTH(CAST(date_int AS CHAR)) != 8 THEN
        RETURN NULL;
    END IF;
    SET result_date = STR_TO_DATE(CAST(date_int AS CHAR), '%Y%m%d');
    RETURN result_date;
END $$
DROP PROCEDURE IF EXISTS reservation_create_folio $$
CREATE PROCEDURE reservation_create_folio(IN reservation_name VARCHAR(255))
BEGIN
    DECLARE v_owner VARCHAR(255);
    DECLARE v_customer VARCHAR(255);
    DECLARE v_check_in_date DATE;  -- Changed from INT to DATE
    DECLARE v_check_out_date DATE; -- Changed from INT to DATE

    -- Get reservation details
    SELECT
        `owner`,
        customer,
        check_in_date,
        check_out_date
    INTO
        v_owner,
        v_customer,
        v_check_in_date,
        v_check_out_date
    FROM
        `tabHotel Reservation`
    WHERE
        name = reservation_name;

    -- Insert into tabFolio
    INSERT INTO `tabFolio` (
        name,
        linked_reservation,
        guest,
        folio_status,
        check_in_date,
        check_out_date,
        cashier,
        total_charges,
        total_payments,
        balance
    ) VALUES (
        CONCAT('f-', reservation_name),
        reservation_name,
        v_customer,
        'Open',
        v_check_in_date,
        v_check_out_date,
        v_owner,
        0,
        0,
        0
    );
    UPDATE `tabHotel Reservation`
    SET check_in_completed = TRUE
    WHERE name = reservation_name;
END $$

DELIMITER ;

