// Optional MiSTer top-level profile for the normalized AT machine.
//
// The default project still instantiates module `emu` from PCAT-286.sv.  The
// sys_top selector can instantiate `emu_at` when AT_PROFILE is defined.  This
// profile owns the MiSTer HPS download path and the physical SDRAM pins, so
// the legacy XT chipset is not present as a second SDRAM owner.
`timescale 1ns/1ps

module emu_at
(
`include "sys/emu_ports.vh"
);

    localparam CONF_STR_AT =
        "PCAT-286 AT;P1FC0,AT BIOS:;P1FC3,EGA BIOS:;P1FC2,XTIDE ROM:;";

    wire [35:0] EXT_BUS;
    wire [21:0] gamma_bus;
    // There is no management-extension owner in this first AT profile.
    // Explicitly drive the extension-select bits low so hps_io returns its
    // normal framework response on HPS_BUS instead of observing Z/X.
    assign EXT_BUS[32] = 1'b0;
    assign gamma_bus[21] = 1'b0;

    wire [31:0] joystick_0;
    wire [31:0] joystick_1;
    wire [15:0] joystick_l_analog_0;
    wire [15:0] joystick_l_analog_1;
    wire [1:0]  hps_buttons;
    wire        forced_scandoubler;
    wire        direct_video;
    wire [127:0] hps_status;
    wire [15:0]  hps_status_menumask = 16'h0000;
    wire [10:0]  ps2_key;
    wire          ps2_kbd_clk_out;
    wire          ps2_kbd_data_out;
    wire          ps2_mouse_clk_out;
    wire          ps2_mouse_data_out;
    wire [7:0]    uart_mode;

    wire        ioctl_download;
    wire [15:0] ioctl_index;
    wire        ioctl_wr;
    wire [26:0] ioctl_addr;
    wire [15:0] ioctl_data;
    wire        ioctl_wait;

    // No legacy PS/2 device is instantiated in this profile.  hps_io still
    // supplies its decoded event stream, which is translated into the AT
    // 8042 host-byte boundary below.
    wire ps2_kbd_clk_in  = 1'b1;
    wire ps2_kbd_data_in = 1'b1;
    wire ps2_mouse_clk_in  = 1'b1;
    wire ps2_mouse_data_in = 1'b1;

    hps_io #(
        .CONF_STR (CONF_STR_AT),
        .PS2DIV   (2000),
        .PS2WE    (1),
        .WIDE     (1)
    ) hps_io_at (
        .clk_sys              (CLK_50M),
        .HPS_BUS              (HPS_BUS),
        .EXT_BUS              (EXT_BUS),
        .gamma_bus            (gamma_bus),
        .forced_scandoubler   (forced_scandoubler),
        .direct_video         (direct_video),
        .buttons              (hps_buttons),
        .status               (hps_status),
        .status_menumask      (hps_status_menumask),
        .video_rotated        (1'b0),
        .new_vmode            (1'b0),
        .info_req             (1'b0),
        .info                 (8'h00),
        .status_in            (128'h0),
        .status_set           (1'b0),
        .uart_mode            (uart_mode),
        .ps2_key              (ps2_key),
        .ps2_kbd_clk_in       (ps2_kbd_clk_in),
        .ps2_kbd_data_in      (ps2_kbd_data_in),
        .ps2_kbd_clk_out      (ps2_kbd_clk_out),
        .ps2_kbd_data_out     (ps2_kbd_data_out),
        .ps2_mouse_clk_in     (ps2_mouse_clk_in),
        .ps2_mouse_data_in    (ps2_mouse_data_in),
        .ps2_mouse_clk_out    (ps2_mouse_clk_out),
        .ps2_mouse_data_out   (ps2_mouse_data_out),
        .joystick_0           (joystick_0),
        .joystick_1           (joystick_1),
        .joystick_l_analog_0  (joystick_l_analog_0),
        .joystick_l_analog_1  (joystick_l_analog_1),
        .ioctl_download       (ioctl_download),
        .ioctl_index          (ioctl_index),
        .ioctl_wr             (ioctl_wr),
        .ioctl_addr           (ioctl_addr),
        .ioctl_dout           (ioctl_data),
        .ioctl_wait           (ioctl_wait),
        .ioctl_upload_req     (1'b0),
        .ioctl_upload_index   (8'h00),
        .ioctl_din            (16'h0000)
    );

    wire        physical_idle;
    wire [12:0] sdram_address;
    wire        sdram_cke;
    wire        sdram_cs;
    wire        sdram_ras;
    wire        sdram_cas;
    wire        sdram_we;
    wire [1:0]  sdram_ba;
    wire [15:0] sdram_dq_in;
    wire [15:0] sdram_dq_out;
    wire        sdram_dq_io;
    wire        sdram_ldqm;
    wire        sdram_udqm;
    logic       sdram_initialized_q;

    assign sdram_dq_in = SDRAM_DQ;
    assign SDRAM_DQ = ~sdram_dq_io ? sdram_dq_out : 16'hzzzz;
    assign SDRAM_CLK = CLK_50M;
    assign SDRAM_A   = sdram_address;
    assign SDRAM_CKE = sdram_cke;
    assign SDRAM_BA  = sdram_ba;
    assign SDRAM_nCS = sdram_cs;
    assign SDRAM_nRAS = sdram_ras;
    assign SDRAM_nCAS = sdram_cas;
    assign SDRAM_nWE  = sdram_we;
    assign SDRAM_DQML = sdram_ldqm;
    assign SDRAM_DQMH = sdram_udqm;

    // physical_idle is a transaction-state signal and therefore drops for
    // every SDRAM access.  The HPS loader needs a monotonic initialization
    // indication so an active ROM word is not reset at the next command.
    always_ff @(posedge CLK_50M or posedge RESET) begin
        if (RESET)
            sdram_initialized_q <= 1'b0;
        else if (physical_idle)
            sdram_initialized_q <= 1'b1;
    end

    wire        loader_valid;
    wire        loader_write;
    wire [23:0] loader_address;
    wire [1:0]  loader_byte_enable;
    wire [15:0] loader_data_out;
    wire        loader_accept;
    wire        loader_ready;
    wire [2:0]  bios_protect_flag;
    wire        main_rom_loaded;
    wire        ega_rom_loaded;
    wire        xtide_rom_loaded;
    wire        loader_active;
    wire        loader_protocol_error;

    spk286_at_hps_rom_loader u_at_hps_rom_loader (
        .clk                (CLK_50M),
        .reset              (RESET),
        .sdram_initialized  (sdram_initialized_q),
        .ioctl_download     (ioctl_download),
        .ioctl_index        (ioctl_index[7:0]),
        .ioctl_wr           (ioctl_wr),
        .ioctl_addr         (ioctl_addr[24:0]),
        .ioctl_data         (ioctl_data),
        .ioctl_wait         (ioctl_wait),
        .loader_valid       (loader_valid),
        .loader_write       (loader_write),
        .loader_address     (loader_address),
        .loader_byte_enable (loader_byte_enable),
        .loader_data_out    (loader_data_out),
        .loader_accept      (loader_accept),
        .loader_ready       (loader_ready),
        .bios_protect_flag  (bios_protect_flag),
        .main_rom_loaded    (main_rom_loaded),
        .ega_rom_loaded     (ega_rom_loaded),
        .xtide_rom_loaded   (xtide_rom_loaded),
        .load_active        (loader_active),
        .protocol_error     (loader_protocol_error)
    );

    wire        cpu_memory_valid;
    wire        cpu_memory_command_valid;
    wire        cpu_memory_write;
    wire        cpu_memory_code_fetch;
    wire [3:0]  cpu_memory_cycle_class;
    wire [23:0] cpu_memory_address;
    wire [1:0]  cpu_memory_byte_enable;
    wire [15:0] cpu_memory_data_out;
    wire        cpu_memory_accept;
    wire        cpu_memory_ready;
    wire [15:0] cpu_memory_read_data;
    wire        cpu_memory_read_data_valid;

    wire        dma_memory_valid;
    wire        dma_memory_write;
    wire        dma_memory_read;
    wire [23:0] dma_memory_address;
    wire [1:0]  dma_memory_byte_enable;
    wire [15:0] dma_memory_data_out;
    wire        dma_memory_accept;
    wire        dma_memory_ready;
    wire [15:0] dma_memory_data_in;

    wire        refresh_memory_valid;
    wire [23:0] refresh_memory_address;
    wire        refresh_memory_accept;
    wire        refresh_memory_ready;

    wire        backend_valid;
    wire        backend_command_valid;
    wire [1:0]  backend_owner;
    wire        backend_write;
    wire        backend_refresh;
    wire        backend_code_fetch;
    wire [3:0]  backend_cycle_class;
    wire [23:0] backend_address;
    wire [1:0]  backend_byte_enable;
    wire [15:0] backend_data_out;
    wire        backend_accept;
    wire        backend_ready;
    wire [15:0] backend_read_data;
    wire        backend_read_data_valid;
    wire        memory_port_protocol_error;

    spk286_at_mister_memory_port u_at_memory_port (
        .clk                    (CLK_50M),
        .reset                  (RESET),
        .cpu_valid              (cpu_memory_valid),
        .cpu_command_valid      (cpu_memory_command_valid),
        .cpu_write              (cpu_memory_write),
        .cpu_code_fetch         (cpu_memory_code_fetch),
        .cpu_cycle_class        (cpu_memory_cycle_class),
        .cpu_address            (cpu_memory_address),
        .cpu_byte_enable        (cpu_memory_byte_enable),
        .cpu_data_out           (cpu_memory_data_out),
        .cpu_accept             (cpu_memory_accept),
        .cpu_ready              (cpu_memory_ready),
        .cpu_read_data          (cpu_memory_read_data),
        .cpu_read_data_valid    (cpu_memory_read_data_valid),
        .loader_valid           (loader_valid),
        .loader_write           (loader_write),
        .loader_address         (loader_address),
        .loader_byte_enable     (loader_byte_enable),
        .loader_data_out        (loader_data_out),
        .loader_accept          (loader_accept),
        .loader_ready           (loader_ready),
        .loader_read_data       (),
        .dma_valid              (dma_memory_valid),
        .dma_write              (dma_memory_write),
        .dma_address            (dma_memory_address),
        .dma_byte_enable        (dma_memory_byte_enable),
        .dma_data_out           (dma_memory_data_out),
        .dma_accept             (dma_memory_accept),
        .dma_ready              (dma_memory_ready),
        .dma_read_data          (dma_memory_data_in),
        .refresh_valid          (refresh_memory_valid),
        .refresh_address        (refresh_memory_address),
        .refresh_accept         (refresh_memory_accept),
        .refresh_ready          (refresh_memory_ready),
        .backend_valid          (backend_valid),
        .backend_command_valid  (backend_command_valid),
        .backend_owner          (backend_owner),
        .backend_write          (backend_write),
        .backend_refresh        (backend_refresh),
        .backend_code_fetch     (backend_code_fetch),
        .backend_cycle_class    (backend_cycle_class),
        .backend_address        (backend_address),
        .backend_byte_enable    (backend_byte_enable),
        .backend_data_out       (backend_data_out),
        .backend_accept         (backend_accept),
        .backend_ready          (backend_ready),
        .backend_read_data      (backend_read_data),
        .backend_read_data_valid(backend_read_data_valid),
        .protocol_error         (memory_port_protocol_error)
    );

    wire        sdram_owner_protocol_error;
    spk286_at_mister_sdram_owner u_at_sdram_owner (
        .clk                    (CLK_50M),
        .reset                  (RESET),
        .request_valid          (backend_valid),
        .request_command_valid  (backend_command_valid),
        .request_owner_refresh  (backend_refresh),
        .request_write          (backend_write),
        .request_code_fetch     (backend_code_fetch),
        .request_cycle_class    (backend_cycle_class),
        .request_address        (backend_address),
        .request_byte_enable    (backend_byte_enable),
        .request_data_out       (backend_data_out),
        .request_accept         (backend_accept),
        .request_ready          (backend_ready),
        .request_read_data      (backend_read_data),
        .request_read_data_valid(backend_read_data_valid),
        .physical_idle          (physical_idle),
        .protocol_error         (sdram_owner_protocol_error),
        .sdram_address           (sdram_address),
        .sdram_cke               (sdram_cke),
        .sdram_cs                (sdram_cs),
        .sdram_ras               (sdram_ras),
        .sdram_cas               (sdram_cas),
        .sdram_we                (sdram_we),
        .sdram_ba                (sdram_ba),
        .sdram_dq_in             (sdram_dq_in),
        .sdram_dq_out            (sdram_dq_out),
        .sdram_dq_io             (sdram_dq_io),
        .sdram_ldqm              (sdram_ldqm),
        .sdram_udqm              (sdram_udqm)
    );

    logic counter_clock;
    logic periodic_tick;
    logic second_tick;
    logic [25:0] tick_counter;
    always_ff @(posedge CLK_50M or posedge RESET) begin
        if (RESET) begin
            counter_clock <= 1'b0;
            periodic_tick <= 1'b0;
            second_tick   <= 1'b0;
            tick_counter  <= 26'd0;
        end else begin
            counter_clock <= ~counter_clock;
            periodic_tick <= (tick_counter[11:0] == 12'h000);
            second_tick   <= (tick_counter == 26'd49_999_999);
            if (tick_counter == 26'd49_999_999)
                tick_counter <= 26'd0;
            else
                tick_counter <= tick_counter + 1'b1;
        end
    end

    wire keyboard_byte_valid;
    wire [7:0] keyboard_byte = ps2_key[7:0];
    logic ps2_key_toggle_q;
    always_ff @(posedge CLK_50M or posedge RESET) begin
        if (RESET)
            ps2_key_toggle_q <= 1'b0;
        else
            ps2_key_toggle_q <= ps2_key[10];
    end
    assign keyboard_byte_valid = ps2_key[10] ^ ps2_key_toggle_q;

    wire at_machine_reset = RESET | !main_rom_loaded;
    wire cpu_fault;
    wire machine_protocol_error;

    spk286_at_machine u_at_machine (
        .clk                    (CLK_50M),
        .reset                  (at_machine_reset),
        .execute_enable         (1'b1),
        .counter_clock          (counter_clock),
        .refresh_enable         (1'b1),
        .keyboard_byte_valid    (keyboard_byte_valid),
        .keyboard_byte          (keyboard_byte),
        .periodic_tick          (periodic_tick),
        .second_tick             (second_tick),
        .parity_event           (1'b0),
        .channel_check_event    (1'b0),
        .external_nmi_event     (1'b0),
        .memory_request_valid   (cpu_memory_valid),
        .memory_command_valid   (cpu_memory_command_valid),
        .memory_write           (cpu_memory_write),
        .memory_code_fetch      (cpu_memory_code_fetch),
        .memory_cycle_class     (cpu_memory_cycle_class),
        .memory_address         (cpu_memory_address),
        .memory_byte_enable     (cpu_memory_byte_enable),
        .memory_data_out        (cpu_memory_data_out),
        .memory_accept          (cpu_memory_accept),
        .memory_ready           (cpu_memory_ready),
        .memory_read_data       (cpu_memory_read_data),
        .memory_read_data_valid (cpu_memory_read_data_valid),
        .dma_memory_valid       (dma_memory_valid),
        .dma_memory_write       (dma_memory_write),
        .dma_memory_read        (dma_memory_read),
        .dma_memory_address     (dma_memory_address),
        .dma_memory_byte_enable (dma_memory_byte_enable),
        .dma_memory_data_out    (dma_memory_data_out),
        .dma_memory_accept      (dma_memory_accept),
        .dma_memory_ready       (dma_memory_ready),
        .dma_memory_data_in     (dma_memory_data_in),
        .refresh_memory_valid   (refresh_memory_valid),
        .refresh_memory_address (refresh_memory_address),
        .refresh_memory_accept  (refresh_memory_accept),
        .refresh_memory_ready   (refresh_memory_ready),
        .cpu_fault              (cpu_fault),
        .protocol_error         (machine_protocol_error)
    );

    // The AT video/media ownership boundary is the next profile milestone;
    // keep the board outputs deterministic while CPU, BIOS and SDRAM paths
    // are brought up independently.
    assign CLK_VIDEO    = CLK_50M;
    assign CE_PIXEL     = 1'b0;
    assign VIDEO_ARX    = 13'd4;
    assign VIDEO_ARY    = 13'd3;
    assign VGA_R        = 8'h00;
    assign VGA_G        = 8'h00;
    assign VGA_B        = 8'h00;
    assign VGA_HS       = 1'b0;
    assign VGA_VS       = 1'b0;
    assign VGA_DE       = 1'b0;
    assign VGA_F1       = 1'b0;
    assign VGA_SL       = 2'b00;
    assign VGA_SCALER   = 1'b0;
    assign VGA_DISABLE  = 1'b0;
    assign HDMI_FREEZE  = 1'b0;
    assign HDMI_BLACKOUT = 1'b0;
    assign HDMI_BOB_DEINT = 1'b0;
    assign LED_USER     = cpu_fault | machine_protocol_error |
                          memory_port_protocol_error |
                          sdram_owner_protocol_error |
                          loader_protocol_error;
    assign LED_POWER    = 2'b00;
    assign LED_DISK     = {1'b0, main_rom_loaded};
    assign BUTTONS      = hps_buttons;
    assign AUDIO_L      = 16'h0000;
    assign AUDIO_R      = 16'h0000;
    assign AUDIO_S      = 1'b0;
    assign AUDIO_MIX    = 2'b00;
    assign ADC_BUS      = 4'hz;
    assign SD_SCK       = 1'bz;
    assign SD_MOSI      = 1'bz;
    assign SD_CS        = 1'bz;
    assign DDRAM_CLK    = CLK_50M;
    assign DDRAM_ADDR   = 29'h0;
    assign DDRAM_BURSTCNT = 8'h0;
    assign DDRAM_RD     = 1'b0;
    assign DDRAM_DIN    = 64'h0;
    assign DDRAM_BE     = 8'h0;
    assign DDRAM_WE     = 1'b0;
    assign UART_RTS     = 1'b0;
    assign UART_TXD     = 1'b1;
    assign UART_DTR     = 1'b0;
    assign USER_OUT     = 7'h00;

endmodule
