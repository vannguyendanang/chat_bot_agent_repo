select * from banktransaction;
select * from bankaccount where AccountNumber = "3423346";

update banktransaction set TransferStatus = "Sent" where AccountNumber = "3423346";


select * from checkpoints where thread_id = "Q_2";
select * from checkpoint_blobs where thread_id = "Q_2";
select * from checkpoint_migrations;
select * from checkpoint_writes where thread_id = "Q_2";

delete from checkpoints where thread_id like "Q%";
delete from checkpoint_blobs where thread_id like "Q%";
delete from checkpoint_writes where thread_id like "Q%";