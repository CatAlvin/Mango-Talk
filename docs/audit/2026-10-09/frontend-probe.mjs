// Runs unchanged component functions with controlled network/keyboard fixtures.
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const dir=path.dirname(fileURLToPath(import.meta.url));
const source=fs.readFileSync(path.resolve(dir,'../../../frontend/src/views/ChatView.vue'),'utf8');
function fn(name){
  const start=source.search(new RegExp(`(?:async )?function ${name}\\(`));
  const tail=source.slice(start);
  const end=tail.slice(1).search(/\n(?:async )?function |\nwatch\(/);
  return tail.slice(0,end+1);
}
const results={};
let calls=0;
const keyboard={handleSendMessage(){calls++}};
vm.createContext(keyboard); vm.runInContext(fn('handleComposerKeydown'),keyboard);
keyboard.handleComposerKeydown({key:'Enter',shiftKey:false,isComposing:true,preventDefault(){}});
results.ime_enter_triggers_send=calls;
const sent=[];
const sendContext={draftMessage:{value:'audit duplicate'},wsRef:{value:{readyState:1,send(value){sent.push(JSON.parse(value))}}},WebSocket:{OPEN:1},replyDraft:{value:null},sending:{value:true},uploading:{value:true},sendError:{value:''},pendingMessageText:{value:''},pendingAttachmentStoredName:{value:''},pendingAckTimer:{value:null},clearPendingAckTimer(){},setTimeout(){return 1},resetPendingSendState(){},console};
vm.createContext(sendContext);vm.runInContext(fn('handleSendMessage'),sendContext);
await sendContext.handleSendMessage(); await sendContext.handleSendMessage();
results.send_while_already_sending_and_uploading=sent.length;
let resolveUpload;
const uploadPromise=new Promise(resolve=>resolveUpload=resolve);
const roomASent=[],roomBSent=[];
const uploadContext={wsRef:{value:{readyState:1,send(x){roomASent.push(x)}}},WebSocket:{OPEN:1},draftMessage:{value:''},replyDraft:{value:null},sending:{value:false},uploading:{value:false},sendError:{value:''},pendingMessageText:{value:''},pendingAttachmentStoredName:{value:''},pendingAckTimer:{value:null},clearPendingAckTimer(){},setTimeout(){return 1},resetPendingSendState(){},uploadAttachment(){return uploadPromise},console};
vm.createContext(uploadContext);vm.runInContext(fn('handleUploadAndSendAttachment'),uploadContext);
const pending=uploadContext.handleUploadAndSendAttachment({name:'fixture.txt'});
uploadContext.wsRef.value={readyState:1,send(x){roomBSent.push(x)}};
resolveUpload({attachment_type:'file',stored_name:'fixture.txt'});
await pending;
results.upload_started_in_room_a_sent_to={room_a:roomASent.length,room_b:roomBSent.length};
fs.writeFileSync(path.join(dir,'frontend-results.json'),JSON.stringify(results,null,2));
console.log(JSON.stringify(results,null,2));
