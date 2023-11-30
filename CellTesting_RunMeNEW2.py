# !/usr/bin/env python3
import pyvisa as visa
from datetime import datetime
import serial
import time
import keyboard
from DL3000 import DL3000
from DP800 import DP800

again = 1  # boolean for while loop to repeat test


# Input function with integer validation
def inputNumber(message, minX, maxX, nType):
    userInput = 0
    while True:
        try:
            if nType == "INTEGER":
                userInput = int(input(message))
            elif nType == "FLOAT":
                userInput = float(input(message))
        except ValueError or (userInput < minX or userInput > maxX):
            print("Invalid Input! Try again.")
            continue
        else:
            return userInput
        # End input function


# Run the source at 20 Amps and write results
def runSource(startTimeS, maxVS, sourceCurrentS, chargeTimeS, oldReplyS, csvFileS, bTestS):
    rigolSource.cc(maxVS, sourceCurrentS)
    print(str(sourceCurrentS) + "Amps Charging")
    counterSkip = 0
    doOnce = 1
    newTimeS = 0
    cMeasuredS = float(rigolSource.current())  # Measure the current
    while (cMeasuredS >= minCharge or counterSkip < 15) and bTestS[1] == 1:  # Run while current greater than 6.5A
        vMeasuredS = float(rigolLoad.voltage())  # Measure the voltage
        cMeasuredS = float(rigolSource.current())  # Measure the current
        counterSkip += 1
        oldReplyS = writeData(startTimeS, vMeasuredS, cMeasuredS, csvFileS, oldReplyS)
        if keyboard.is_pressed("q"):
            oldReplyS = "@"  # Set the test to End
        if oldReplyS > "":
            if oldReplyS[0] == "@":
                bTestS[1] = 0  # Set the test to End
                print("Test Ended Early\n")
                csvFileS.write("Test Ended Early\n")
        if cMeasuredS > 0.5 and doOnce == 1:  # Don't start count until Current is >0
            newTimeS = time.time()
            doOnce = 0
        if chargeTimeS > 0 and cMeasuredS > 0.5:  # CD Test selected
            pulseTrackerS = time.time() - newTimeS
            if pulseTrackerS >= chargeTimeS:
                break
    rigolSource.disable()  # Disable Source once at 6.5A
    return bTestS


# End runSource Function

# Run the load at 'current' Amps and write results
def runLoad(startTimeL, minVL, currentL, dischargeTimeL, pulseTimeL, oldReplyL, csvFileL, bTestL):
    rigolLoad.cc(currentL)
    print(str(- 1 * currentL) + "Amps Discharging")
    newTimeL = 0
    counterSkipL = 0
    doOnceL = 1
    vMeasuredL = float(rigolLoad.voltage())  # Measure the voltage
    cMeasuredL = float(rigolLoad.current())
    oldReplyL = writeData(startTimeL, vMeasuredL, cMeasuredL, csvFileL, oldReplyL)
    while (vMeasuredL > minVL or counterSkipL < 10) and (bTestL[0] == 0 and bTestL[1] == 1):  # Check that voltage is greater than 3.05V
        vMeasuredL = float(rigolLoad.voltage())  # Measure the voltage
        cMeasuredL = float(rigolLoad.current())
        counterSkipL = counterSkipL + 1
        oldReplyL = writeData(startTimeL, vMeasuredL, cMeasuredL, csvFileL, oldReplyL)
        if keyboard.is_pressed("q"):
            oldReplyL = "@"  # Set the test to End
        if oldReplyL > "":
            if oldReplyL[0] == "@":
                bTestL[1] = 0  # Set the test to End
                print("Test Ended Early\n")
                file.write("Test Ended Early\n")
        if cMeasuredL > 0.5 and doOnceL == 1:  # Don't start count until Current is >0
            newTimeL = time.time()
            doOnceL = 0
        if (pulseTimeL > 0 or dischargeTimeL > 0) and cMeasuredL > 0.5:  # RC or CD Test selected and current is drawing
            pulseTrackerL = time.time() - newTimeL
            if pulseTimeL > 0 and pulseTrackerL >= pulseTimeL:
                rigolLoad.disable()  # Disable the load to view voltage recovery
                prevMeasureL = 0
                counterN = 0
                while (counterN < 10 or abs(vMeasuredL - prevMeasureL) > 0.0001) and (bTestL[0] == 0 and bTestL[1] == 1):
                    # Check that voltage is settled
                    counterN = counterN + 1
                    prevMeasureL = vMeasuredL
                    vMeasuredL = float(rigolLoad.voltage())  # Measure the voltage
                    cMeasuredL = float(rigolLoad.current())
                    oldReplyL = writeData(startTimeL, vMeasuredL, cMeasuredL, csvFileL, oldReplyL)
                    if keyboard.is_pressed("q"):
                        oldReplyL = "@"  # Set the test to End
                    if oldReplyL[0] == "@":
                        bTestL[1] = 0  # Set the test to End
                        print("Test Ended Early\n")
                        file.write("Test Ended Early\n")
                rigolLoad.cc(current)
                newTimeL = time.time()  # Reset pulse time tracker
            elif 0 < dischargeTimeL <= pulseTrackerL:  # CD Test selected
                break
    if vMeasuredL <= minVL:
        bTestL[0] = 1
    rigolLoad.disable()  # Disable Load once around 3.05V
    prevMeasureL = 0  # Take final recover voltage
    counterN = 0
    while (counterN < 10 or abs(vMeasuredL - prevMeasureL) > 0.0001) and bTestL[1] == 1:  # Check that voltage is settled
        counterN = counterN + 1
        prevMeasureL = vMeasuredL
        vMeasuredL = float(rigolLoad.voltage())  # Measure the voltage
        cMeasuredL = float(rigolLoad.current())
        oldReplyL = writeData(startTimeL, vMeasuredL, cMeasuredL, csvFileL, oldReplyL)
        if keyboard.is_pressed("q"):
            oldReplyL = "@"  # Set the test to End
        # Write Current as negative for Load
        if oldReplyL[0] == "@":
            bTestL[1] = 0  # Set the test to End
            print("Test Ended Early\n")
            file.write("Test Ended Early\n")
    return bTestL
    # End runLoad Function


# Function to Write file
def writeData(startTimeW, vMeasuredW, cMeasuredW, csvFileW, oldReplyW):
    testTimeW = (time.time() - startTimeW)  # Grab timestamp
    if comPort != 99:  # Arduino interface selected
        arduino.write("$".encode())  # Send temperature request to arduino
        if arduino.in_waiting > numChars:  # Verify expected number of characters in Serial buffer
            tempReply = arduino.readline()  # Read line from Arduino Serial buffer
            tempReply = tempReply.decode('utf-8')  # Decode Arduino message from binary to string
            oldReplyW = tempReply[0:][:-2]  # Remove \r and \n characters (Carriage Return and New Line)
        print("{:4.2f}\t{:4.3f}\t{:4.3f}\t{}".format(testTimeW, vMeasuredW, cMeasuredW, oldReplyW))  # Write to screen
        csvFileW.write(
            "{:4.2f}\t{:4.3f}\t{:4.3f}\t{}\n".format(testTimeW, vMeasuredW, cMeasuredW, oldReplyW))  # log the data
        time.sleep(sampleTime)  # Sleep for required sample time
    else:  # Standalone Selected
        print("{:4.2f}\t{:4.3f}\t{:4.3f}".format(testTimeW, vMeasuredW, cMeasuredW))  # Write to screen
        csvFileW.write("{:4.2f}\t{:4.3f}\t{:4.3f}\n".format(testTimeW, vMeasuredW, cMeasuredW))  # log the data
        time.sleep(sampleTime)  # Sleep for required sample time
    return oldReplyW


# Function to Write file

# Function to Write Meta Data to file
def writeMeta():
    timeString = datetime.now().strftime("%Y_%m_%d__%H_%M_%S")  # Create Date/Time string and file for data export
    if comPort != 99:  # Arduino interface selected
        filepath = "./CSV/TEMP/Cell" + str(cellID) + testType + "Test_on" + timeString + "Load" + str \
            (current) + "Amps" + "_" + str(wantTemp) + "Cdeg.csv"
    else:
        filepath = "./CSV/Cell" + str(cellID) + testType + "Test_on" + timeString + "Load" + str(current) + "Amps.csv"
    print("CellID:\t{}\tDate/Time:\t{}".format(cellID, timeString))  # Print metadata to terminal
    print("MaxLoadCurrent:\t{:4.3f}\tMaxSourceCurrent:\t{:4.3f}".format(current, sourceCurrent))
    print("MinCurrent:\t{:4.3f}\tMinVoltage:\t{:4.3f}".format(minC, minV))
    print("NomVoltage:\t{:4.3f}\tMaxVoltage:\t{:4.3f}".format(nomV, maxV))
    print("NumberPulses:\t{:4.3f}\tPulseTime:\t{:4.3f}".format(pulseN, pulseTime))
    print("ChargeTime:\t{:4.3f}\tDischargeTime:\t{:4.3f}".format(chargeTime, dischargeTime))
    if comPort != 99:  # Arduino interface selected
        print("MaxTemp:\t{:4.3f}\tTestTemp:\t{:4.3f}\n".format(maxT, wantTemp))
        print("Duration\tVolt\tCurrent\tAmbTemp\tT1\tT2\tT3\tT4\tT5\tT6\tT7")
    else:
        print("Duration\tVolt\tCurrent")
    file = open(filepath, "a")  # Write metadata to .csv file
    file.write("CellID:\t{}\tDate/Time:\t{}\n".format(cellID, timeString))
    file.write("MaxLoadCurrent:\t{:4.3f}\tMaxSourceCurrent:\t{:4.3f}\n".format(current, sourceCurrent))
    file.write("MinCurrent:\t{:4.3f}\tMinVoltage:\t{:4.3f}\n".format(minC, minV))
    file.write("NomVoltage:\t{:4.3f}\tMaxVoltage:\t{:4.3f}\n".format(nomV, maxV))
    file.write \
        ("NumberPulses:\t{:4.3f}\tPulseTime:\t{:4.3f}\t(Resistance Capacitance Test Only)\n".format(pulseN, pulseTime))
    file.write("ChargeTime:\t{:4.3f}\tDischargeTime:\t{:4.3f}\t(Charge Discharge Test Only)\n".format(chargeTime,
                                                                                                      dischargeTime))
    if comPort != 99:  # Arduino interface selected
        file.write("MaxTemp:\t{:4.3f}\tTestTemp:\t{:4.3f}\n".format(maxT, wantTemp))
        file.write("Duration\tVolt\tCurrent\tAmbTemp\tT1\tT2\tT3\tT4\tT5\tT6\tT7\n")
    else:
        file.write("Duration\tVolt\tCurrent\n")
    return file


# End Write Meta

# Print Startup
def printStartup():
    print("     .-----------,-.-------.                               ")
    print("       |:_D_H_B_W//(+)\OSU|:                               ")
    print("    ___||=======// ,--.\===.|  ___                         ")
    print("  .'.'''\}____.'/ | (__)\__|\.'.'''.      GFR Capstone Oven")
    print("  | |'''||._       '---'__   `-|'''|       Battery Testing ")
    print("  | |'''||. '-.___  ` -'--'     `-.| ___                   ")
    print("  | |'''|| '-.'.'''.----._     .---:'.'''.                 ")
    print("  `.'_'.'|   | |'''|_____ `. /\ \___||_''|                 ")
    print("          '-.| |''_/_____\ \/  \ \_____\_|                 ")
    print("             | |'|____    ',\ '.__/  ____|                 ")
    print("             `.'__.'  `'---'-'---'-'.'__.'                 ")
    print(" ")
    print(" Hold down 'q' during any test to end the test. ")


# Start pyvisa resource manager and load instruments ##
# This is where new instruments and their corredsponding IDS are added ##
rm = visa.ResourceManager()
rigolLoad = DL3000(rm.open_resource('USB0::6833::3601::DL3D000000001::0::INSTR'))  # Load
rigolSource = DP800(rm.open_resource('USB0::6833::3601::DP8A000001::0::INSTR'))  # Source

# Main Function
while again:
    # Reset states
    # !!!NOTE: This information is cell specific!!!
    # THIS DATA IS FOR CELL: "Tesla" COSMX 01 95B0D0HD-13Ah
    # DO NOT EXCEED THESE VALUES ########
    #       Maximum Tesla Cell Voltage - 4.28V
    #       Nominal Tesla Cell Voltage - 3.73V (Storage)
    #       Minimum Tesla Cell Voltage - 3.00V
    #       Maximum Tesla Cell Charge Current - >100A
    #       Minimum Tesla Cell Charge/Discharge Current - 6.5A(0.5C)
    #       where C is cell capacity in Amps/Hour
    #       Maximum Telsa Cell Continuous Duty Temperature - 55Celsius
    #       Minimum Tesla Cell Continuous Duty Temperature - 5Celsius
    #       Maximum Rigol Source Current - 20A
    #       Maximum Rigol Load Current - 70A
    # DO NOT EXCEED THESE VALUES ########

    # Start of global variables
    # based on cell values above
    # UPDATE IF CELL MODEL CHANGES:
    rateC = 13  # C rate for Telsa Cell (where C is cell capacity in Amps/Hour)
    maxT = 55  # Max Selectable Temp Celcius
    minT = 0  # Min Selectable Temp Celcius
    wantTemp = 0  # Wanted ambient Temp variable
    maxV = 4.27  # Max Voltage 4.27
    nomV = 3.8  # Nominal (Storage) Voltage
    minV = 3.05  # Min Voltage
    minC = 6.5  # Min Load Current 6.5 A
    minCharge = 1.0  # Min Charge Current 1.0 A
    maxC = 60  # Max Current
    maxSourceCurrent = 20.0  # Maximum from Rigol DP813A (Default)
    sourceCurrent = 20.0  # Variable for source Current

    # not related to cell model
    # DO NOT UPDATE UNLESS MODIFYING FUNCTIONALITY:
    preCharge = 0  # boolean for whether to charge the cell before running test
    arduino = ""  # Variable for communications port for Arduino
    testTime = 0  # Variable for test Duration
    newTime = 0  # Variable to keep track of time Pulses
    pulseTime = 0  # Period of time for Pulse Discharge (RC Test)
    chargeTime = 0  # Period of time for Charge (CD Test)
    dischargeTime = 0  # Period of time for Discharge (CD Test)
    pulseTracker = 0  # Variable to hold pulse counter
    pulseN = 0  # Number of pulses to perform for Resistance/Capacitance Test
    prevMeasure = 0  # Variable for voltage measurement loop
    iType = "INTEGER"  # String declarations
    fType = "FLOAT"  #
    filepath = ""  #
    oldReply = ""  #
    tReply = ""  # String declarations
    testType = "CC"  # Default Test Type
    numChars = 46  # Number of characters expected from Arduino Serial Transmission
    sampleTime = 0.05  # Default sample time period (Seconds)
    bQuit = 0 # boolean for quit during heating

    rigolLoad.reset()  # Reset to factory settings
    rigolSource.reset()  # Reset to factory settings
    printStartup()

    # Run all prompt scripts
    cellID = inputNumber("Please enter the Cell ID Number (1-500): ", 1, 500, iType)  # Prompt for Cell ID Number port
    # Prompt for Test Type '0' for CC '1' for RC '2' for CD
    isTest = inputNumber \
        ("Please enter '0' for Current Capacity (CC), '1' for Resistance Capacitance (RC), '2' for Charge Discharge ("
         "CD) Test, '3' to Make Cell Nominal Voltage (0-3): ",
         0, 3, iType)
    if isTest == 3:  # Charge/Discharge Test selected: Prompt for pulse times in seconds
        testType = "NOM"
    else:
        preCharge = inputNumber \
            ("Please enter '1' to start test without precharging or '0' to Charge the cell to Max before testing ("
             "0-1): ", 0, 1, iType)
    if isTest == 2:  # Charge/Discharge Test selected: Prompt for pulse times in seconds
        testType = "CD"
        chargeTime = inputNumber("Please enter an integer number of seconds to Charge for CD Test (1-30[S]): ", 1, 30, iType)
        # Prompt for current charge value
        sourceCurrent = inputNumber \
            ("Please enter an integer Source current value (" + str(0.0) + "-" + str(maxSourceCurrent) + "[A]): ", 0, maxSourceCurrent, fType)
        dischargeTime = inputNumber("Please enter an integer number of seconds to Discharge for CD Test (1-30[S]): ", 1,
                                    30, iType)
    # Prompt for current discharge value
    current = inputNumber("Please enter an integer Load current value (" + str(minC) + "-" + str(maxC) + "[A]): ", minC,
                          maxC, fType)
    if isTest == 1:  # Resistance/Capacitance Test selected: Prompt for number of pulses for test
        testType = "RC"
        pulseTime = inputNumber("Please enter an integer number for discharge pulse time for RC Test in ms (10-1500): ", 10, 1500, iType)
        pulseTime = pulseTime / 1000
    comPort = inputNumber("Please enter Arduino COM Port number or 99 for Standalone (0-99): ", 0, 99,
                          iType)  # Prompt for usb arduino COM port
    if comPort != 99:  # Arduino interface selected/Comport chosen: Connect arduino
        # Prompt for temperature value
        wantTemp = inputNumber("Please enter an integer temperature value (" + str(minT) + "-" + str(maxT) + " [C]): ", minT, maxT, iType)
        arduino = serial.Serial('/dev/ttyUSB' + str(comPort), 115200, timeout=None)  # Setup Arduino Serial Connection
        print("Heating Up")
        time.sleep(2)
        arduino.write(str(wantTemp).encode())  # Send wanted temperature to arduino
        time.sleep(0.5)
        dataRaw = arduino.readline()  # Wait for arduino signal that temperature reached
        data = dataRaw.decode('utf-8')
        data = data[0:][:-2]
        while not data == '&' and bQuit == 0:
           dataRaw = arduino.readline()  # Temp Reached
            data = dataRaw.decode('utf-8')
            data = data[0:][:-2]
            if not (data == '&' or data == ''):
                tReply = data
                print(tReply)
            if keyboard.is_pressed("q"):
                bQuit = 1
                bRunTest = [endCD, 0] # Set the test to End
                arduino.write("^").encode  # Send end signal to arduino
                print("Test Ended Early\n")
                file.write("Test Ended Early\n")
    if bQuit == 0:
        vMeasured = float(rigolLoad.voltage())
        cMeasured = float(rigolLoad.current())
        startTime = time.time()
        file = writeMeta()  # Write the MetaData and create the file
        endCD = 0
        bRunTest = [endCD, 1]
        oldReply = writeData(startTime, vMeasured, cMeasured, file, oldReply)
        if isTest == 3:
            if vMeasured > nomV:
                print("Discharging to Nominal Voltage: {}V".format(nomV))
                bRunTest = runLoad(startTime, nomV, current, dischargeTime, pulseTime, oldReply, file, bRunTest)
                # Discharge cell to nominal voltage for storage
            else:
                print("Charging to Nominal Voltage: {}V".format(nomV))
                bRunTest = runSource(startTime, nomV, sourceCurrent, chargeTime, oldReply, file, bRunTest)  # Charge cell to nominal
                # voltage for storage
        else:
            if preCharge == 0:  # Charge cell to maximum voltage
                print("Charging to Maximum Voltage: {}V".format(maxV))
                bRunTest = runSource(startTime, maxV, sourceCurrent, 0, oldReply, file, bRunTest)  # Charge cell to maximum
                # voltage
            if isTest == 2:  # Is Charge/Discharge Test
                while vMeasured > minV and bRunTest[0] == 0 and bRunTest[1] == 1:
                    print("Charging for {:4.3f} Seconds".format(chargeTime))
                    bRunTest = runSource(startTime, maxV, sourceCurrent, chargeTime, oldReply, file, bRunTest)  # Charge cell to
                    # maximum voltage
                    print("Discharging for {:4.3f} Seconds".format(dischargeTime))
                    bRunTest = runLoad(startTime, minV, current, dischargeTime, pulseTime, oldReply, file, bRunTest)
                    # Discharge cell at chosen amperage
                    vMeasured = float(rigolLoad.voltage())
            else:
                print("Discharging at {} Amps".format(current))
                bRunTest = runLoad(startTime, minV, current, dischargeTime, pulseTime, oldReply, file, bRunTest)
                # Discharge cell at chosen amperage
            print("Charging to nominal")
            bRunTest = runSource(startTime, nomV, sourceCurrent, 0, oldReply, file, bRunTest)  # Charge cell to nominal
            # voltage for storage
    file.close()
    # Prompt to run identical test on same cell
    if bRunTest[1] == 0:
        if comPort != 99:  # Arduino interface selected
            arduino.write("^".encode())  # Send emergency shutoff request to arduino
        print("Test ended early!!!!!!!!!!!!!!!!!!!")
    again = inputNumber("Please enter '1' to test the connected cell again, '0' to quit: ", 0, 1, iType)
    if comPort != 99:  # Arduino interface selected
        arduino.close()
# End Main