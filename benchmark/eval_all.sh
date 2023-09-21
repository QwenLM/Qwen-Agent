
nohup python inference_and_execute.py --task gsm8k --model gpt-4 -n 20 -f > log/log_gsm8k_gpt-4.txt 2>&1 &
nohup python inference_and_execute.py --task gsm8k --model gpt-3.5-turbo-0613 -n 20 -f > log/log_gsm8k_gpt-3.5-turbo-0613.txt 2>&1 &


# i=0
for task in visualization all_ci gsm8k
do
nohup python inference_and_execute.py --task ${task} --model gpt-4 -n 10 -f > log/log_${task}_gpt-4.txt 2>&1 &
nohup python inference_and_execute.py --task ${task} --model gpt-3.5-turbo-0613 -n 10 -f > log/log_${task}_gpt-3.5-turbo-0613.txt 2>&1 &
# i=$((i+1))
# export CUDA_VISIBLE_DEVICES=$i && nohup torchrun --nproc_per_node 1 --master_port $(shuf -i 10000-32000 -n 1) inference_and_execute.py --task ${task} --model llama2 -f > log/log_${task}_llama2.txt 2>&1 &
# i=$((i+1))
# export CUDA_VISIBLE_DEVICES=$i && nohup torchrun --nproc_per_node 1 --master_port $(shuf -i 10000-20000 -n 1) inference_and_execute.py --task ${task} --model codellama -f > log/log_${task}_llama2.txt 2>&1 &
# i=$((i+1))
# export CUDA_VISIBLE_DEVICES=$i && nohup python inference_and_execute.py --task ${task} --model internlm -f > log/log_${task}_internlm.txt 2>&1 &
done


# export CUDA_VISIBLE_DEVICES=1 && nohup torchrun --nproc_per_node 1 --master_port (shuf -i 10000-20000 -n 1) inference_and_execute.py --task visualization --model codellama > log/log_visualization_llama2.txt 2>&1 &

# export CUDA_VISIBLE_DEVICES=0 && nohup torchrun --nproc_per_node 1 --master_port $(shuf -i 10000-20000 -n 1) inference_and_execute.py --task visualization --model llama2 > log/log_visualization_llama2.txt 2>&1 &

# export CUDA_VISIBLE_DEVICES=0 && nohup torchrun --nproc_per_node 1 --master_port $(shuf -i 10000-20000 -n 1) inference_and_execute.py --task visualization --model llama2 > log/log_visualization_llama2.txt 2>&1 &


# python inference_and_execute.py --task visualization --model  -n 20 -f
# python inference_and_execute.py --task visualization --model  -n 20 -f
# python inference_and_execute.py --task visualization --model gpt-3.5-turbo-0613 -n 20 -f
# python inference_and_execute.py --task visualization --model gpt-3.5-turbo-0613 -n 20 -f



# export CUDA_VISIBLE_DEVICES=0 && torchrun --nproc_per_node 1 --master_port $(shuf -i 10000-32000 -n 1) inference_and_execute.py --task all_ci --model llama2 -f


export CUDA_VISIBLE_DEVICES=1 && nohup python inference_and_execute.py --task ci_open_questions --model qwen-14b-chat > log/log_ci_open_questions_qwen-14b-chat.txt 2>&1 &


# export CUDA_VISIBLE_DEVICES=0 && nohup python inference_and_execute.py --task all_ci --model qwen-14b-chat > log/log_all_ci_qwen-14b-chat.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=1 && nohup python inference_and_execute.py --task visualization --model qwen-14b-chat --eval-only > log/log_visualization_qwen-14b-chat.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=0 && nohup python inference_and_execute.py --task gsm8k --model qwen-14b-chat -f > log/log_gsm8k_qwen-14b-chat.txt 2>&1 &


# export CUDA_VISIBLE_DEVICES=4 && nohup python inference_and_execute.py --task all_ci --model qwen-7b-chat-1.1 > log/log_all_ci_qwen-7b-chat-1.1.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=6 && nohup python inference_and_execute.py --task visualization --model qwen-7b-chat-1.1 --eval-only > log/log_visualization_qwen-7b-chat-1.1.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=1 && nohup python inference_and_execute.py --task gsm8k --model qwen-7b-chat-1.1 > log/log_gsm8k_qwen-7b-chat-1.1.txt 2>&1 &



# python inference_and_execute.py --task all_ci --model gpt-4 -n > log/log_all_ci_gpt-4.txt
# python inference_and_execute.py --task all_ci --model gpt-3.5-turbo-0613 > log/log_all_ci_gpt-3.5-turbo-0613.txt

python inference_and_execute.py --task visualization --model gpt-4 > log/log_visualization_gpt-4.txt
python inference_and_execute.py --task visualization --model gpt-3.5-turbo-0613 --eval-only > log/log_visualization_gpt-3.5-turbo-0613.txt

# python inference_and_execute.py --task all_ci --model gpt-4 > log/log_visualization_gpt-4.txt
# python inference_and_execute.py --task all_ci --model gpt-3.5-turbo-0613 > log/log_visualization_gpt-3.5-turbo-0613.txt

# python inference_and_execute.py --task all_ci --model gpt-4 > log/log_all_ci_gpt-4.txt



export CUDA_VISIBLE_DEVICES=7 && nohup python inference_and_execute.py --task visualization --model llama-2-13b-chat > log/log_visualization_llama-2-13b-chat-hf.txt 2>&1 &


export CUDA_VISIBLE_DEVICES=3,4 && nohup torchrun --nproc_per_node 2 --master_port $(shuf -i 30000-32000 -n 1) inference_and_execute.py --task all_ci --model llama-2-13b-chat > log/log_all_ci_llama-2-13b-chat.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=4,5 && nohup torchrun --nproc_per_node 2 --master_port $(shuf -i 30000-32000 -n 1) inference_and_execute.py --task visualization --model llama-2-13b-chat > log/log_visualization_llama-2-13b-chat.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=6,7 && nohup torchrun --nproc_per_node 2 --master_port $(shuf -i 30000-32000 -n 1) inference_and_execute.py --task gsm8k --model llama-2-13b-chat --eval-only > log/log_gsm8k_llama-2-13b-chat.txt 2>&1 &


export CUDA_VISIBLE_DEVICES=7 && nohup python inference_and_execute.py --task gsm8k --model llama-2-13b-chat --eval-only > log/log_gsm8k_eval_llama-2-13b-chat.txt 2>&1 &


export CUDA_VISIBLE_DEVICES=0,1 && nohup torchrun --nproc_per_node 2 --master_port $(shuf -i 30000-32000 -n 1) inference_and_execute.py --task all_ci --model codellama-13b-instruct > log/log_all_ci_codellama-13b-instruct.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=2,3 && nohup torchrun --nproc_per_node 2 --master_port $(shuf -i 30000-32000 -n 1) inference_and_execute.py --task visualization --model codellama-13b-instruct > log/log_visualization_codellama-13b-instruct.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=0,1 && nohup torchrun --nproc_per_node 2 --master_port $(shuf -i 30000-32000 -n 1) inference_and_execute.py --task gsm8k --model codellama-13b-instruct > log/log_gsm8k_codellama-13b-instruct.txt 2>&1 &



export CUDA_VISIBLE_DEVICES=0,1 && nohup torchrun --nproc_per_node 2 --master_port $(shuf -i 30000-32000 -n 1) inference_and_execute.py --task all_ci --model codellama-13b-instruct -f > log/log_all_ci_codellama-13b-instruct_new.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=0,1 && nohup torchrun --nproc_per_node 2 --master_port $(shuf -i 30000-32000 -n 1) inference_and_execute.py --task gsm8k --model codellama-13b-instruct -f > log/log_gsm8k_codellama-13b-instruct_new.txt 2>&1 &



export CUDA_VISIBLE_DEVICES=7 && nohup python inference_and_execute.py --task ci_open_questions --model codellama-13b-instruct -f > log/log_ci_open_questions_codellama-13b-instruct_new.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=5 && nohup python inference_and_execute.py --task all_ci --model qwen-1.8b-chat > log/log_all_ci_qwen-1.8b-chat.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=6 && nohup python inference_and_execute.py --task visualization --model qwen-1.8b-chat > log/log_visualization_qwen-1.8b-chat.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=7 && nohup python inference_and_execute.py --task gsm8k --model qwen-1.8b-chat > log/log_gsm8k_qwen-1.8b-chat.txt 2>&1 &


#==================
export CUDA_VISIBLE_DEVICES=0 && nohup python inference_and_execute.py --task all_ci --model qwen-7b-chat -f > log/log_all_ci_qwen-7b-chat.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=1 && nohup python inference_and_execute.py --task visualization --model qwen-7b-chat -f > log/log_visualization_qwen-7b-chat.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=2 && nohup python inference_and_execute.py --task gsm8k --model qwen-7b-chat -f > log/log_gsm8k_qwen-7b-chat.txt 2>&1 &



export CUDA_VISIBLE_DEVICES=6 && nohup torchrun --nproc_per_node 1 --master_port $(shuf -i 30000-32000 -n 1)




export CUDA_VISIBLE_DEVICES=1 && nohup torchrun --nproc_per_node 1 --master_port $(shuf -i 30000-32000 -n 1) inference_and_execute.py --task all_ci --model llama-2-7b-chat -f > log/log_all_ci_llama-2-7b-chat.txt 2>&1 &
export CUDA_VISIBLE_DEVICES=5 && nohup torchrun --nproc_per_node 1 --master_port $(shuf -i 30000-32000 -n 1) inference_and_execute.py --task gsm8k --model llama-2-7b-chat -f > log/log_gsm8k_llama-2-7b-chat.txt 2>&1 &

# export CUDA_VISIBLE_DEVICES=4 && nohup torchrun --nproc_per_node 1 --master_port $(shuf -i 30000-32000 -n 1) inference_and_execute.py --task visualization --model llama-2-7b-chat -f > log/log_visualization_llama-2-7b-chat.txt 2>&1 &





export CUDA_VISIBLE_DEVICES=2 && nohup torchrun --nproc_per_node 1 --master_port $(shuf -i 30000-32000 -n 1) inference_and_execute.py --task all_ci --model codellama-7b-instruct -f > log/log_all_ci_codellama-7b-instruct.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=3 && nohup torchrun --nproc_per_node 1 --master_port $(shuf -i 30000-32000 -n 1) inference_and_execute.py --task gsm8k --model codellama-7b-instruct -f > log/log_gsm8k_codellama-7b-instruct.txt 2>&1 &

# export CUDA_VISIBLE_DEVICES=4 && nohup torchrun --nproc_per_node 1 --master_port $(shuf -i 30000-32000 -n 1) inference_and_execute.py --task visualization --model codellama-7b-instruct -f > log/log_visualization_codellama-7b-instruct.txt 2>&1 &





export CUDA_VISIBLE_DEVICES=6 && nohup python inference_and_execute.py --task visualization --model internlm -f > log/log_visualization_internlm.txt 2>&1 &
export CUDA_VISIBLE_DEVICES=7 && nohup python inference_and_execute.py --task gsm8k --model internlm -f > log/log_gsm8k_internlm.txt 2>&1 &
export CUDA_VISIBLE_DEVICES=0 && nohup python inference_and_execute.py --task all_ci --model internlm --eval-only --code-exec-only > log/log_all_ci_internlm_eval.txt 2>&1 &


# export CUDA_VISIBLE_DEVICES=6,7 && torchrun --nproc_per_node 2 --master_port $(shuf -i 30000-32000 -n 1) inference_and_execute.py --task gsm8k --model llama-2-13b-chat



export CUDA_VISIBLE_DEVICES=0 && nohup python inference_and_execute.py --task visualization --model llama-2-13b-chat --eval-only > log/log_visualization_eval_llama-2-13b-chat.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=1 && nohup python inference_and_execute.py --task visualization --model llama-2-7b-chat --eval-only > log/log_visualization_eval_llama-2-7b-chat.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=2 && nohup python inference_and_execute.py --task visualization --model codellama-7b-instruct --eval-only > log/log_visualization_eval_codellama-7b-instruct.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=3 && nohup python inference_and_execute.py --task visualization --model codellama-13b-instruct --eval-only > log/log_visualization_eval_codellama-13b-instruct.txt 2>&1 &


nohup python inference_and_execute.py --task ci_open_questions --model codellama-7b-instruct --eval-only > log/log_ci_open_questions_eval_codellama-7b-instruct.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=3 && nohup nohup torchrun --nproc_per_node 1 inference_and_execute.py --task ci_open_questions --model llama-2-7b-chat > log/log_ci_open_questions_llama-2-7b-chat.txt 2>&1 &


#==========
# qwen
# 1.8b

export CUDA_VISIBLE_DEVICES=0 && nohup python inference_and_execute.py --task all_ci --model qwen-1.8b-chat -f > log/log_all_ci_qwen-1.8b-chat.txt 2>&1 &
export CUDA_VISIBLE_DEVICES=0 && nohup python inference_and_execute.py --task gsm8k --model qwen-1.8b-chat --eval-only > log/log_gsm8k_qwen-1.8b-chat.txt 2>&1 &

# 14b
export CUDA_VISIBLE_DEVICES=1 && nohup python inference_and_execute.py --task all_ci --model qwen-14b-chat -f > log/log_all_ci_qwen-14b-chat.txt 2>&1 &
export CUDA_VISIBLE_DEVICES=1 && nohup python inference_and_execute.py --task gsm8k --model qwen-14b-chat --eval-only > log/log_gsm8k_qwen-14b-chat.txt 2>&1 &

# 7b-1.1
export CUDA_VISIBLE_DEVICES=2 && nohup python inference_and_execute.py --task all_ci --model qwen-7b-chat-1.1 -f > log/log_all_ci_qwen-7b-chat-1.1.txt 2>&1 &
export CUDA_VISIBLE_DEVICES=2 && nohup python inference_and_execute.py --task gsm8k --model qwen-7b-chat-1.1 --eval-only > log/log_gsm8k_qwen-7b-chat-1.1.txt 2>&1 &

# # 7b-1.1 v0.1
# export CUDA_VISIBLE_DEVICES=3 && nohup python inference_and_execute.py --task all_ci --model qwen-7B-chat-1.1_v0.1 --eval-only > log/log_all_ci_qwen-7B-chat-1.1_v0.1_eval.txt 2>&1 &
# export CUDA_VISIBLE_DEVICES=2 && nohup python inference_and_execute.py --task gsm8k --model qwen-7B-chat-1.1_v0.1 -f > log/log_gsm8k_qwen-7B-chat-1.1_v0.1.txt 2>&1 &

# # qwen-14b-chat-rl
# export CUDA_VISIBLE_DEVICES=0 && nohup python inference_and_execute.py --task all_ci --model qwen-14b-chat-rl -f > log/log_all_ci_qwen-14b-chat-rl.txt 2>&1 &
# export CUDA_VISIBLE_DEVICES=2 && nohup python inference_and_execute.py --task gsm8k --model qwen-14b-chat-rl -f > log/log_gsm8k_qwen-14b-chat-rl.txt 2>&1 &


# 7b
export CUDA_VISIBLE_DEVICES=3 && nohup python inference_and_execute.py --task all_ci --model qwen-7b-chat -f > log/log_all_ci_qwen-7b-chat.txt 2>&1 &
export CUDA_VISIBLE_DEVICES=3 && nohup python inference_and_execute.py --task gsm8k --model qwen-7b-chat --eval-only > log/log_gsm8k_qwen-7b-chat.txt 2>&1 &


# internlm 7b
export CUDA_VISIBLE_DEVICES=0 && nohup python inference_and_execute.py --task all_ci --model internlm -f > log/log_all_ci_internlm.txt 2>&1 &
export CUDA_VISIBLE_DEVICES=4 && nohup python inference_and_execute.py --task gsm8k --model internlm --eval-only > log/log_gsm8k_internlm.txt 2>&1 &


# llama
# 7b
export CUDA_VISIBLE_DEVICES=5 && nohup python inference_and_execute.py --task all_ci --model llama-2-7b-chat -f > log/log_all_ci_llama-2-7b-chat.txt 2>&1 &
export CUDA_VISIBLE_DEVICES=5 && nohup python inference_and_execute.py --task gsm8k --model llama-2-7b-chat --eval-only > log/log_gsm8k_llama-2-7b-chat.txt 2>&1 &

# 13b
export CUDA_VISIBLE_DEVICES=6 && nohup python inference_and_execute.py --task all_ci --model llama-2-13b-chat -f > log/log_all_ci_llama-2-13b-chat.txt 2>&1 &
export CUDA_VISIBLE_DEVICES=6 && nohup python inference_and_execute.py --task gsm8k --model llama-2-13b-chat --eval-only > log/log_gsm8k_llama-2-13b-chat.txt 2>&1 &

# codellama
# 7b
export CUDA_VISIBLE_DEVICES=7 && nohup python inference_and_execute.py --task all_ci --model codellama-7b-instruct -f > log/log_all_ci_codellama-7b-instruct.txt 2>&1 &
export CUDA_VISIBLE_DEVICES=7 && nohup python inference_and_execute.py --task gsm8k --model codellama-7b-instruct --eval-only > log/log_gsm8k_codellama-7b-instruct.txt 2>&1 &

# 13b
export CUDA_VISIBLE_DEVICES=0 && nohup python inference_and_execute.py --task all_ci --model codellama-13b-instruct -f > log/log_all_ci_codellama-13b-instruct.txt 2>&1 &
export CUDA_VISIBLE_DEVICES=0 && nohup python inference_and_execute.py --task gsm8k --model codellama-13b-instruct --eval-only > log/log_gsm8k_codellama-13b-instruct.txt 2>&1 &

# gpt
nohup python inference_and_execute.py --task all_ci --model gpt-4 -n 20 > log/log_all_ci_gpt-4.txt 2>&1 &
nohup python inference_and_execute.py --task all_ci --model gpt-3.5-turbo-0613 -n 20 > log/log_all_ci_gpt-3.5-turbo-0613.txt 2>&1 &
