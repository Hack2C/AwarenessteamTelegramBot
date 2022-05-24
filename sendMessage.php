<?php
function sendMessage($bot_id,$chat_id,$disable_notification,$message_text)
{
        $ch = curl_init('https://api.telegram.org/bot'.$bot_id.'/sendMessage');
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, 1);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);

        $param = array(
                'chat_id' => $chat_id,
                'parse_mode' => 'html',
                'disable_notification' => $disable_notification,
                'text' => $message_text
        );

        curl_setopt($ch, CURLOPT_POST, 1);
        curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query($param));

        $result = curl_exec($ch);
        curl_close($ch);

        return $result;
}
?>