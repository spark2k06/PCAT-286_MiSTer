LIBRARY ieee;
USE ieee.std_logic_1164.ALL;
USE ieee.numeric_std.ALL;
USE std.env.ALL;

ENTITY at_scaler_luminance_tb IS END;
ARCHITECTURE test OF at_scaler_luminance_tb IS
  SIGNAL clk : std_logic := '0';
  SIGNAL h_rgb,v_rgb : unsigned(23 DOWNTO 0) := (OTHERS=>'0');
  SIGNAL hm,vm : unsigned(2 DOWNTO 0) := "100";
  SIGNAL adaptive : std_logic_vector(1 DOWNTO 0) := "01";
  SIGNAL hf,vf : unsigned(7 DOWNTO 0) := (OTHERS=>'0');
  SIGNAL lum,ref_lum : unsigned(7 DOWNTO 0);
  SIGNAL ta,tb,ref_ta,ref_tb : signed(9 DOWNTO 0);
  SIGNAL phases,ref_phases : std_logic_vector(143 DOWNTO 0);
  SIGNAL address,ref_address : natural;
BEGIN
  clk<=NOT clk AFTER 3.367 ns;
  candidate: ENTITY work.polyfetch_candidate
    PORT MAP(clk,h_rgb,v_rgb,hm,vm,adaptive,hf,vf,lum,ta,tb,phases,address);
  reference: ENTITY work.polyfetch_reference
    PORT MAP(clk,h_rgb,v_rgb,hm,vm,adaptive,hf,vf,ref_lum,ref_ta,ref_tb,ref_phases,ref_address);
  PROCESS
    TYPE values_t IS ARRAY(natural RANGE <>) OF natural;
    CONSTANT edge_values : values_t := (0,1,63,127,128,129,254,255);
    VARIABLE rng : unsigned(31 DOWNTO 0) := x"C031B17E";
    VARIABLE count,h_count,v_count,both_count,hold_count : natural := 0;
    VARIABLE held_lum,previous_lum : natural := 0;
    VARIABLE use_h,use_v : boolean := false;
    PROCEDURE step IS
      VARIABLE value : natural;
      VARIABLE pixel : unsigned(23 DOWNTO 0);
    BEGIN
      WAIT UNTIL rising_edge(clk);
      -- The mode/enable pair is registered one cycle before pixel selection.
      value:=held_lum;
      IF use_h OR use_v THEN
        pixel:=h_rgb;
        IF use_v THEN pixel:=v_rgb; v_count:=v_count+1;
        ELSE h_count:=h_count+1; END IF;
        IF use_h AND use_v THEN both_count:=both_count+1; END IF;
        value:=0;
        FOR channel IN 0 TO 2 LOOP
          IF to_integer(pixel(channel*8+7 DOWNTO channel*8))>value THEN
            value:=to_integer(pixel(channel*8+7 DOWNTO channel*8));
          END IF;
        END LOOP;
      ELSE hold_count:=hold_count+1;
      END IF;
      use_h:=hm/="000" AND adaptive(0)='1';
      use_v:=vm/="000" AND adaptive(1)='1';
      WAIT FOR 1 ps;
      IF count>20 THEN
        ASSERT lum=to_unsigned(held_lum,8) REPORT "Luminance value/latency changed" SEVERITY failure;
        ASSERT ta=to_signed(256-previous_lum,10) AND tb=to_signed(previous_lum,10)
          REPORT "Adaptive weights lost alignment" SEVERITY failure;
        ASSERT lum=ref_lum AND ta=ref_ta AND tb=ref_tb AND address=ref_address AND phases=ref_phases
          REPORT "PolyFetch differs from the pre-split scaler at cycle " & integer'image(count) SEVERITY failure;
      END IF;
      previous_lum:=held_lum; held_lum:=value; count:=count+1;
      WAIT UNTIL falling_edge(clk);
    END;
    PROCEDURE randomize IS
    BEGIN
      rng:=rng XOR shift_left(rng,13);
      rng:=rng XOR shift_right(rng,17);
      rng:=rng XOR shift_left(rng,5);
    END;
  BEGIN
    -- Prime all coefficient stages, then exercise extended hold windows.
    FOR mode IN 0 TO 3 LOOP
      adaptive<=std_logic_vector(to_unsigned((mode+1) MOD 4,2));
      FOR i IN 0 TO 31 LOOP
        h_rgb<=to_unsigned(i*7919,24); v_rgb<=to_unsigned(16#FFFFFF#-i*97,24);
        step;
      END LOOP;
    END LOOP;
    -- All boundary RGB combinations with all adaptive flags and axis enables.
    FOR flags IN 0 TO 3 LOOP
      adaptive<=std_logic_vector(to_unsigned(flags,2));
      FOR enables IN 0 TO 3 LOOP
        hm<="000"; vm<="000";
        IF enables MOD 2=1 THEN hm<="100"; END IF;
        IF enables>=2 THEN vm<="100"; END IF;
        FOR r IN edge_values'RANGE LOOP
          FOR g IN edge_values'RANGE LOOP
            FOR b IN edge_values'RANGE LOOP
              h_rgb<=to_unsigned(edge_values(r)*65536+edge_values(g)*256+edge_values(b),24);
              v_rgb<=to_unsigned((255-edge_values(b))*65536+(255-edge_values(r))*256+255-edge_values(g),24);
              hf<=to_unsigned(count MOD 256,8); vf<=to_unsigned((count*13) MOD 256,8);
              step;
            END LOOP;
          END LOOP;
        END LOOP;
      END LOOP;
    END LOOP;
    -- Changing pixels, fractions, flags and modes on consecutive cycles.
    FOR i IN 0 TO 65535 LOOP
      randomize; h_rgb<=rng(23 DOWNTO 0); adaptive<=std_logic_vector(rng(25 DOWNTO 24));
      hm<=rng(28 DOWNTO 26); vm<=rng(31 DOWNTO 29);
      randomize; v_rgb<=rng(23 DOWNTO 0); hf<=rng(31 DOWNTO 24);
      randomize; vf<=rng(7 DOWNTO 0);
      step;
    END LOOP;
    FOR i IN 0 TO 15 LOOP step; END LOOP;
    ASSERT h_count>1000 AND v_count>1000 AND both_count>1000 AND hold_count>1000
      REPORT "Insufficient adaptive axis/hold coverage" SEVERITY failure;
    REPORT "AT_SCALER_LUMINANCE_PASS cycles=" & integer'image(count) &
      " horizontal=" & integer'image(h_count) & " vertical=" & integer'image(v_count) &
      " both=" & integer'image(both_count) & " held=" & integer'image(hold_count);
    stop;
  END PROCESS;
END;
