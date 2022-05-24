<?php
// Import of Secrets and send function
include '/etc/nginx/bot_secrets.php';
include 'sendMessage.php';

// Get BOT_TOKEN for identification and authorization
$bot_id = BOT_TOKEN;
$table_name = DB_TABLE;

// Parse User Message
$json_out = json_decode(file_get_contents('php://input'), true);
$chat_id = $json_out['message']['chat']['id'];
$type = $json_out['message']['chat']['type'];
$message = $json_out['message']['text'];
$message_id = $json_out['message']['message_id'];

// Set some default values for later
$sent = false;
$chat_id_found = false;
$message_from_awareness = false;
$user_has_pseudo = false;
$pseudo = '';
$targetChat_id = '';
$blockChat_id = '';
$dbid = '';

// SQL Snippets we use. This isnt best practice, but it works very well
$sql_getAllUsers = 'SELECT id, chat_id, pseudo From ' . $table_name . ';';
$sql_insertNewUser= 'INSERT INTO ' . $table_name . '(chat_id,pseudo) Values("' . $chat_id . '","");';
$sql_blockUser = 'UPDATE ' . $table_name . ' SET pseudo= "blocked" WHERE chat_id = "' . $blockChat_id . '";';
$sql_updatePseudo = 'UPDATE ' . $table_name . ' SET pseudo = "' . $pseudo . '" WHERE chat_id = "'. $chat_id .'";';

//Startnachricht (&#10 = new line)
if (stripos($message, '/start') === 0 && $type == 'private') {
        sendMessage($bot_id, $chat_id, false, 'Hi! &#10Dies hier ist ein Bot! Dir wird automatisch ein Pseudonym zugeteilt. Deine Daten sind absolut Anonym, bis du selbst entscheidest sie mit uns zu teilen.');
}

//Chat-ID Abfrage (For All Users, but used mainly for Awarenessteam)
if (strpos(strtolower($message), 'chatid') !== false && !$sent) {
        $sent = true;
        sendMessage($bot_id, $chat_id, false, 'Deine Chat-ID lautet: <b>' . $chat_id . '</b>');
}

// Create connection to db
$conn = mysqli_connect(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME);
// Check connection to db
if (!$conn) {
        sendMessage($bot_id,$chat_id,false,'DBConnection Error! Please contact admin.');
}

// Message from AT?
if($chat_id == AT_CHAT_ID) {
        $message_from_awareness = true;
}

// Getting all ChatId-Pseudonym connections
$result_user = mysqli_query($conn, $sql_getAllUsers);

// Are there any users?
if (mysqli_num_rows($result_user) > 0) {
    // As long as there are Rows
    while ($row = mysqli_fetch_assoc($result_user)) {
        // Check, if Chat id is found
        if($row["chat_id"] == $chat_id) {
            // save pseudonym for later
            $pseudo = $row["pseudo"];
            $chat_id_found = true;
        }
    }
}

// Is there a pseudo for the user?
if ($chat_id_found && $pseudo != '') {
        $user_has_pseudo = true;
}

// User is NOT in DB and not the Awarenessteam
if(!$chat_id_found && !$message_from_awareness) {
    if (mysqli_query($conn, $sql_insertNewUser)) {
        echo "New record created successfully";
    } else {
        echo "Error: " . $sql_insertNewUser . "<br>" . mysqli_error($conn);
    }
}

// Set a Pseudonym if there is no. 
if (!$user_has_pseudo && !$message_from_awareness) {
    // If the user has no pseudo and message is not from awareness
    // Get Again all Users, cause maybe the user is new in the database
    $result_user = mysqli_query($conn, $sql_getAllUsers);
    // Checking, if there is any User in DB
    if (mysqli_num_rows($result_user) > 0) {
        // search for the user (chat_id)
        while ($row = mysqli_fetch_assoc($result_user)) {
            if($row['chat_id'] == $chat_id) {
                // Get the autoincrementell and unique database id for the user
                $dbid = strval($row['id']);
            }
        }
        // Building a unique pseudonym for the User
        $pseudo = 'Anonymous' . $dbid;
        // Set the Pseudonym for the User
        if (mysqli_query($conn, $sql_updatePseudo)) {
                echo "New record created successfully";
                // Send the Pseudonym to the user, if db entry success
                sendMessage($bot_id, $chat_id, false, 'Dein Pseudonym lautet: ' . $pseudo . '&#10Jede weitere Nachricht wird direkt an das Awarnessteam weitergeleitet.');
          } else {
                echo "Error: " . $sql_updatePseudo . "<br>" . mysqli_error($conn);
          }
        }
}

// forward any user message to AT
if ($user_has_pseudo && !$message_from_awareness && ($pseudo != 'blocked')) {
        $sent = true;
        $targetChat_id = AT_CHAT_ID;
        sendMessage($bot_id,$targetChat_id,false, $pseudo . ' schrieb: &#10 &#10' . $message);
}

// Forward AT Message to User
// check for the command /answer
if(strpos(strtolower($message),'/answer') !== false) {
    // check if message is from AT
    if($message_from_awareness) {
        $result_user = mysqli_query($conn, $sql_getAllUsers);
        while ($row = mysqli_fetch_assoc($result_user)) {
            // We are checking, if after the pseudonym is a break for a new line thats why, we are adding '&#10' 
            $pseudo = $row['pseudo'] . "&#10";
            if(strpos(strtolower($message),strtolower($pseudo)) !== false) {
                $targetChat_id = $row['chat_id'];
                $pseudo = $row['pseudo'];
            }
        }
        // We are searching for the position of the pseudonym and are cutting everything before the pseudonym
        // so we are not forwarding the command and the Pseudonym
        $forward_message = substr($message,strpos(strtolower($message),strtolower($pseudo))+strlen($pseudo));
        sendMessage($bot_id,$targetChat_id,false,$forward_message);
    }
}

// Give the AT the abbility to block a user, in case of abusing
// Check for the Command /block
if(strpos(strtolower($message),'/block') !== false) {
    if($message_from_awareness) {
        while ($row = mysqli_fetch_assoc($result_user)) {
            // We are checking, if after the pseudonym is a break for a new line thats why, we are adding '&#10' 
            $pseudo = $row['pseudo'] . "&#10";
            if(strpos(strtolower($message),strtolower($pseudo)) !== false) {
                $blockChat_id = $row['chat_id'];
            }
        }
        mysqli_query($conn, $sql_blockUser);
    }
}

mysqli_close($conn);