
This directory is effectively a set of "unit tests" for the schematic and PCB.

**Extra Annotation** are extra properties that get added to nets which allow
more advanced checks. For example,
 * adding clock line and frequency annotations allows the Spartan 6 to check
   that high speed clocks are connected to global clock pins,
 * adding grouping annotation lets PCB checking make sure the lengths are
   matched,
 * adding frequency annotation lets PCB checking make sure track width and
   spacing are correct, (in theory would also allow for automated 
   ["skinny trace"](FIXME:add url here) generation.

-------------------------------------------------------------------------------
-------------------------------------------------------------------------------

# Schematic Checks

These checks are for the schematic level and mainly consist of high level
things (like I/O voltage levels).

A lot of extra annotation information can also be generated based on the
schematic details too.

## Implemented

 - [ ]

-------------------------------------------------------------------------------

## TODO

### Generic Checks

 - [ ] Check that a `XXX_N` has an associated `XXX_P`
 - [ ] Check power rail name formatting;
   * `VCC5V0` - `VCC_5V0` - `VCC5V` - `VCC_5V`
   * `VCC12V`
   * `VCC(([0-9]V[0-9])|([0-9][0-9]V))`

 - [ ] Check for unnamed nets in the schematic
   * Highlight all nets which have the unnamed form of N-XXXXX

---------------------------------------

### DisplayPort

From the DisplayPort connector we can annotate the nets with the following;

 - [ ] Voltage levels - 3.3V everywhere?
 - [ ] Speeds / frequencies (720p, 1080p, or?)
   - [ ] ML lanes - 5.4 GHz
   - [ ] AUX lane - 720 Mbit/s
 
 - [ ] Required impedance - ????
 - [ ] Type - Clock, data.
 - [ ] Group - All nets should be grouped together.

---------------------------------------

### HDMI


#### IP4776CZ38

 - [ ] NC pins on opposite side of TMDS lines are connected correctly.

#### Connector

##### Extra annotation

From the pins on a HDMI connector we can annotate the nets with the following
properties;

 - [ ] Voltage levels
   - [ ] 3.3V for TMDS lines
   - [ ] 3.3V for CEC lines
   - [ ] 5.0V for I2C and ?hot plug?
 - [ ] Speeds / frequencies (720p, 1080p, or?)
   - [ ] TMDS lines in GHz range
   - [ ] CEC ????
   - [ ] I2C 400kHz
 - [ ] Required impedance (balanced 100 Ohm split, giving 50 Ohm)
 - [ ] Type - Clock, data.
 - [ ] Group - All nets should be grouped together.

---------------------------------------

### PMOD



---------------------------------------

### VHDCI

 - [ ] 

#### Extra annotation

From the VHDCI connector we can annotate the nets with the following
properties;

 - [ ] Type - Clock, data.
 - [ ] Speeds / ?frequencies?
 - [ ] Group - All nets should be grouped together.

---------------------------------------

### Spartan 6 checks

Checks for Xilinx Spartan 6 FPGA.

#### Generic checks

 - [ ] Check that `XXX_N` and `XXX_P` terminate on the same Spartan I/O lane.
       IE `TMDS-TX0-2_P` and `TMDS-TX0-2_N` terminate on say,
          `IO_L41N_GCLK8_M1CASN_1` and `IO_L41N_GCLK8_M1CASN_1` pair. 

 - [ ] **HARD** Check that the I/O voltages in a bank are compatible. Check the
       VCC applied to `VCC0_X` matches.


#### Spartan HDMI checks

 - [ ] Check clock pair ends up on GCLK pins.
 - [ ] Check all I/O pins ends up on the same I/O half bank.
 - [ ] Check HDMI TX ports are on bank XXX or XXX.

 - [ ] Pull up resistors on ?TX?

#### Spartan DisplayPort checks

 - [ ] ???


-------------------------------------------------------------------------------
-------------------------------------------------------------------------------

# PCB checks


## Implemented

 - [ ]

-------------------------------------------------------------------------------

## TODO

### Generic Checks

 - [ ] Check that `_N` and `_P` pairs are length matched.
 - [ ] Check that `_N` and `_P` pairs run the majority of time together (so
       they are effectively A/C coupled).

---------------------------------------

### Checks based on annotations

 - [ ] Check the impedance of traces matches annotation.
 - [ ] Check the length of a group of traces matches within tolerances.
 - [ ] Check the  




