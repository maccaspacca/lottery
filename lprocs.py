# Lottery using the Bismuth Blockchain
# Version 1.00
# Date 09/11/2018
# Copyright Maccaspacca 2017 to 2018
# Copyright The Bismuth Foundation 2016 to 2018
# Author Maccaspacca

from Cryptodome.PublicKey import RSA
from Cryptodome.Signature import PKCS1_v1_5
from Cryptodome.Hash import SHA

import configparser as cp

import base64, time, json, connections, log, socks, random, requests

app_log = log.log("lottery.log","INFO", "yes")
app_log.info("logging initiated")

config = cp.ConfigParser()
config.readfp(open(r'lottery.ini'))
app_log.info("Reading configuration file")
lot_address = config.get('Lottery', 'address')
wallet = config.get('Lottery', 'walletpath')
round_length = int(config.get('Lottery', 'rounds'))

pay_it_out = False # don't payout until conditions are met.

def convert_ip_port(ip, some_port):
    """
    Get ip and port, but extract port from ip if ip was as ip:port
    :param ip:
    :param some_port: default port
    :return: (ip, port)
    """
    if ':' in ip:
        ip, some_port = ip.split(':')
    return ip, some_port
	
def get_node():

	try:
		t_ip = "127.0.0.1"
		t_port = "5658"
		s = socks.socksocket()
		s.settimeout(10)
		s.connect((t_ip, int(t_port)))
		app_log.warning("Status: Wallet connected to {}".format(t_ip))
		
	except:
	
	# try the wallet servers api

		rep = requests.get("http://api.bismuth.live/servers/wallet/legacy.json")
		if rep.status_code == 200:
			wallets = rep.json()
			
		sorted_wallets = sorted([wallet for wallet in wallets if wallet['active']], key=lambda k: (k['clients']+1)/(k['total_slots']+2))

		light_ip = ["{}:{}".format(wallet['ip'], wallet['port']) for wallet in sorted_wallets]
		
		some_port = "5658"

		for lip in light_ip:

			try:
				t_ip, t_port = convert_ip_port(lip, some_port)
				s = socks.socksocket()
				s.settimeout(10)
				s.connect((t_ip, int(t_port)))
				app_log.warning("Status: Wallet connected to {}".format(t_ip))
				break

			except Exception as e:
				app_log.warning("Status: Cannot connect to {}".format(t_ip))			
				time.sleep(1)
				
	return t_ip,t_port
	
ip,port = get_node()


def latest():

	try:
		s = socks.socksocket()
		s.settimeout(10)
		s.connect((ip, int(port)))
		connections.send(s, "blocklast", 10)
		block_get = connections.receive(s, 10)
		
		try:
			db_block_height = block_get[0]
			
		except:
			db_block_height = 0
			
		app_log.info("Current block: {}".format(str(db_block_height)))
			
		return db_block_height
		
	except:
		app_log.warning("No connection")


def get_tx_list(addy):

	try:
		s = socks.socksocket()
		s.settimeout(10)
		s.connect((ip, int(port)))
		connections.send(s, "addlist")
		connections.send(s, addy)
		address_tx_list = connections.receive(s)

	except:
		app_log.warning("No connection")
		
	#print(address_tx_list)
	
	#address_tx_lotto = [ll for ll in address_tx_list if "lotto:" in ll[10]] # maybe later :) 
	
	op_last = next(atl[10] for atl in address_tx_list if "lotto:paid:" in atl[10])
	
	#print(op_last)
	
	bl_start = int(op_last.split(':')[2]) + 1
	app_log.info("Block start: {}".format(str(bl_start)))
	
	#print(bl_start)
	
	op_next = next(atl[10] for atl in address_tx_list if "lotto:next:" in atl[10])
	
	bl_stop = int(op_next.split(':')[2])
	app_log.info("Block finish: {}".format(str(bl_stop)))
	
	#print(bl_stop)
	
	tresult = [txl for txl in address_tx_list if txl[0] > (bl_start - 1) and txl[0] < (bl_stop + 1) and txl[3] == lot_address and "lotto:enter" in txl[10].lower()]
	
	#print(tresult)
	
	result = []
	
	# Check they have paid the correct amount.
	# Anything over stays with the house
	# Perhaps make this configurable?
	
	# check each entry has paid
	x = 0
	for tr in tresult:
		if float(tresult[x][4]) >= 1:
			tr.append((x+1))
			result.append(tr)
		x +=1
	
	app_log.info("Entries selected - first run")
	
	#print(result)
	return result,bl_start,bl_stop

	
def keys_load_new(wallet_file=wallet):
	# import keys

	app_log.info("Reading keys")

	with open (wallet_file, 'r') as wallet_file:
		wallet_dict = json.load (wallet_file)

	private_key_readable = wallet_dict['Private Key']
	public_key_readable = wallet_dict['Public Key']
	address = wallet_dict['Address']

	key = RSA.importKey(private_key_readable)

	# public_key_readable = str(key.publickey().exportKey())
	if (len(public_key_readable)) != 271 and (len(public_key_readable)) != 799:
		raise ValueError("Invalid public key length: {}".format(len(public_key_readable)))

	public_key_hashed = base64.b64encode(public_key_readable.encode('utf-8'))

	return key, public_key_readable, private_key_readable, public_key_hashed, address
	

def send_bis(txs): # sends bismuth from a selected address in the wallet
	
	(key, private_key_readable, public_key_readable, public_key_hashed, address) = keys_load_new(wallet)
	
	amount_input = txs[0]
	recipient_input = txs[1]
	openfield_input = txs[2]
	keep_input = txs[3]
	
	try:

		timestamp = '%.2f' % time.time()
		transaction = (str(timestamp), str(address), str(recipient_input), '%.8f' % float(amount_input), str(keep_input), str(openfield_input))  # this is signed
		# print transaction

		h = SHA.new(str(transaction).encode("utf-8"))
		signer = PKCS1_v1_5.new(key)
		signature = signer.sign(h)
		signature_enc = base64.b64encode(signature)
		txid = signature_enc[:56]

		#print("Encoded Signature: %s" % signature_enc.decode("utf-8"))
		#print("Transaction ID: %s" % txid.decode("utf-8"))
		
		mytxid = txid.decode("utf-8")

		verifier = PKCS1_v1_5.new(key)
		
		if verifier.verify(h, signature):
			print("verifier")
			tx_submit = (str(timestamp), str(address), str(recipient_input), '%.8f' % float(amount_input), str(signature_enc.decode("utf-8")), str(public_key_hashed), str(keep_input), str(openfield_input)) #float kept for compatibility
			#print(tx_submit)
			s = socks.socksocket()
			s.settimeout(10)
			s.connect((ip, int(port)))
			connections.send(s, "mpinsert", 10)
			connections.send(s, tx_submit, 10)
			reply = connections.receive(s, 10)
			print(reply)
			mydone = True
			s.close()
			app_log.info("Transaction sent: {}".format(mytxid))
			return mydone, reply, mytxid
			# refresh() experimentally disabled
		else:
			print("Invalid signature")
			reply = "Invalid signature"
			mydone = False
			app_log.warning("Invalid signature")
			return mydone, reply, mytxid
			# enter transaction end
			
	except:
		print("Oops !")
		reply = "Transaction failed - unknown reason"
		mydone = False
		mytxid = "Transaction failed"
		app_log.warning("Transaction failed")
		return mydone, reply, mytxid

def get_winner(potentials):

	app_log.info("Randomly selecting a winner")

	x = random.randint(1,1000) # get a random number between 1 and 1000
	i = 1
	keep_me = False
	
	# choose a random winner for the random number of times
	# for example if x = 200 then make a random choice 200 times and keep the 200th result
	# this makes the choice of each winner more random
	while not keep_me:
		winner = random.choice(valids)
		if i == x:
			keep_me = True
		i += 1

	back_list = [p for p in potentials if p[2] != winner[2]]
	

	#for p in potentials:
		
			#if p[0] != winner[0]:
				#back_list.append(p)
	# send the winning choice back to the program (the list is sent back 3 times)
	# I could imporve this by iterating 3 times within the function and sending the whole list back?
	return winner, back_list
	
raw_list = get_tx_list(lot_address)

x_list = raw_list[0]
start_block = raw_list[1] # start block
end_block = raw_list[2] # end block

print("Lottery round started at block: {}".format(str(start_block)))
print("Lottery round ends at block: {}".format(str(end_block)))

if not x_list:
	app_log.warning("No players found !!!")
	print("No players found !!!")
	quit()
	
if len(x_list) < 3:
	app_log.warning("Only {} players found !!!".format(str(len(x_list))))
	print("Only {} players found !!!".format(str(len(x_list))))
	quit()
	
valids = []

app_log.info("Double checking selected entries")
for l in x_list:

	# Double check it's valid?
	
	if ((start_block - 1) < int(l[0]) < end_block) and float(l[4]) >= 1 and l[3] == lot_address and "lotto:enter" in l[10].lower():
		temp_v = (l[2],l[5][:56],l[12])
		valids.append(temp_v)

valid_entries = len(valids)
#print(valids)
app_log.info("Number of valid entries: {}".format(len(valids)))
print("Number of valid entries: {}".format(len(valids)))

prize_first = float('%.8f' % (0.55 * valid_entries))
app_log.info("First prize: {} BIS".format(str(prize_first)))

prize_second = float('%.8f' % (0.3 * valid_entries))
app_log.info("Second prize: {} BIS".format(str(prize_second)))

prize_third = float('%.8f' % (0.1 * valid_entries))
app_log.info("Third prize: {} BIS".format(str(prize_third)))

winners = []

app_log.info("Getting 3 winners and preparing transaction information")

for w in range(3):
	process_it = get_winner(valids)
	if w == 0:
		tmp_win = (prize_first,process_it[0][0],"1st Prize","lotto:win")
	elif w == 1:
		tmp_win = (prize_second,process_it[0][0],"2nd Prize","lotto:win")
	elif w == 2:
		tmp_win = (prize_third,process_it[0][0],"3rd Prize","lotto:win")

	winners.append(tmp_win)
	
	valids = process_it[1]
	
#open_tmp = "1:{}\n2:{}\n3:{}".format(winners[0][1],winners[1][1],winners[2][1])
open_tmp = ""

# Add a transaction to state this round has been paid
app_log.info("Preparing paid transaction")
tmp_conf = (0,lot_address,open_tmp,"lotto:paid:{}".format(end_block))

winners.append(tmp_conf)

# Add a transaction to tell us when next round ends

app_log.info("Preparing next round end transaction")
tmp_next = (0,lot_address,"","lotto:next:{}".format(end_block + round_length))

winners.append(tmp_next)

# print(winners)

latest_block = latest()

if latest_block > end_block:
	pay_it_out = True
	app_log.info("Sending winning and information transactions")

#"""
for txs in winners:
	if pay_it_out:
		do_send = send_bis(txs)
		time.sleep(5)
		print(do_send)
	else:
		print("No payment made but would have sent\n{}\n".format(txs))
#"""

print("1st prize of {} BIS goes to {}".format(prize_first, winners[0][1]))
print("2nd prize of {} BIS goes to {}".format(prize_second, winners[1][1]))
print("3rd prize of {} BIS goes to {}".format(prize_third, winners[2][1]))
