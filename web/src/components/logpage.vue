<template>
    <v-container>
        <div class="text-md-center">
            <h1>Logs</h1>
        </div>
        <v-list id="logpage">
            <v-list-tile
                    v-for="item in log_list"
                    :key="item.key"
            >
                <v-list-tile-content>
                    <v-list-tile-title v-text="item.message"></v-list-tile-title>
                </v-list-tile-content>

            </v-list-tile>
        </v-list>
    </v-container>
</template>

<script>
    export default {
        name: "logpage",
        data(){
            return{
                log_list: []
            }
        },
        created() {
            this.$options.sockets.onmessage = (data) => {
                var d = JSON.parse(data.data)
                d.key = data.timeStamp
                this.log_list.push(d)
                console.log(data)
            }
        }
    }
</script>

<style scoped>

</style>