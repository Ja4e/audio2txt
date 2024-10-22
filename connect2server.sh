#!/bin/bash

# File to store the server IP address
IP_FILE="$HOME/.server_ip"

# Function to prompt for the server IP address, with an option to use the saved local IP
function get_server_ip {
    if [ -f "$IP_FILE" ]; then
        # Load the saved IP address
        SAVED_IP=$(cat "$IP_FILE")
        
        echo "A saved IP address was found: $SAVED_IP"
        read -p "Do you want to use the saved IP? (y/n): " use_saved_ip
        
        if [ "$use_saved_ip" == "y" ] || [ "$use_saved_ip" == "Y" ]; then
            SERVER_IP=$SAVED_IP
        else
            read -p "Enter the new IP address of the server: " SERVER_IP
        fi
    else
        read -p "Enter the IP address of the server: " SERVER_IP
    fi
    
    # Save the new or selected IP address to the file for future use
    echo "$SERVER_IP" > "$IP_FILE"
}

# Get the current user's home directory (in case running with sudo)
USER_HOME=$(eval echo ~${SUDO_USER})

# Call the function to get the server IP address
get_server_ip

echo "create one if not existing"

# Prompt for the RSA private key location
read -p "Enter the path to your RSA private key (default: $USER_HOME/.ssh/id_rsa): " RSA_KEY
RSA_KEY=${RSA_KEY:-$USER_HOME/.ssh/id_rsa}

# Clear the known_hosts entry for this IP
ssh-keygen -R $SERVER_IP

# Automatically answer "yes" to the "Are you sure you want to continue connecting?" prompt
# Copy RSA key to the server for passwordless authentication (use -f to force copy if necessary)
ssh-keyscan -H $SERVER_IP >> $USER_HOME/.ssh/known_hosts
ssh-copy-id -f -i $RSA_KEY jake@$SERVER_IP

#chacnge it where the audio2txt.py loated
kitty --detach bash -c "cd audio2txt; sleep 2; python audio2txt.py; exec bash" &

echo "run this command"
# change this if not lcoated also it somehow doesnt directly work with ssh 
echo "cd /home/jake/audio2txt && python audio2txt.py"

#um for port 5901 used for noVNC and 5905 and 5906 port for server script (coming up with better script)
ssh -t -i $RSA_KEY -c aes256-ctr -L 5901:localhost:5901 -L 5905:localhost:5905 -L 5906:localhost:5906 jake@$SERVER_IP

