.headers on

.mode csv

SELECT
  t.run_id,
  t.max_flag_submitted,
  m.message_count
FROM
  (
    SELECT
      run_id,
      MAX(
        CAST(
          SUBSTR(
            result_text,
            INSTR(result_text, '(') + 1,
            INSTR(result_text, '/') - INSTR(result_text, '(') - 1
          ) AS INTEGER
        )
      ) AS max_flag_submitted
    FROM tool_calls
    WHERE
      function_name = 'SubmitFlag'
      AND result_text LIKE 'Flag submitted%'
    GROUP BY run_id
  ) AS t
JOIN
  (
    SELECT
      run_id,
      COUNT(*) AS message_count
    FROM messages
    GROUP BY run_id
  ) AS m
  ON t.run_id = m.run_id;
